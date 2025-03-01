import json
import logging
import re
from statistics import mean
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.finetuned_model import FineTunedModel
from app.services.chat import ChatService
from app.config import settings
from openai import OpenAI
from app.utils.blob_storage import download_from_blob_async  # Updated import

logger = logging.getLogger(__name__)

class EvaluationService:
    """
    Service for robustly evaluating a job's RAG and fine-tuned models.

    For each evaluation question, the service:
      - Obtains an answer from the model.
      - (Optionally) Uses provided ground truth and/or oracle answers.
      - Evaluates the answer on multiple metrics:
           - relevancy, faithfulness, completeness, and clarity.
      - If ground truth is provided, also evaluates "correctness".
      - If an oracle is provided, also evaluates "oracle_agreement".
    
    Multiple trials per question are averaged to reduce LLM variability.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_service = ChatService(db)

    def evaluate_answer(self, question: str, answer: str, context: str, 
                        ground_truth: str = None, oracle: str = None, num_trials: int = 1) -> dict:
        """
        Evaluate an answer on several metrics over multiple trials.

        The evaluation prompt now optionally includes:
         - Ground truth: the expected answer.
         - Oracle: an ideal answer.
        The LLM is asked to return a JSON object with keys:
          - relevancy, faithfulness, completeness, clarity
          - correctness (if ground_truth is provided)
          - oracle_agreement (if oracle is provided)

        :param question: The evaluation question.
        :param answer: The model's answer.
        :param context: Aggregated context for the job.
        :param ground_truth: (Optional) The expected answer.
        :param oracle: (Optional) The ideal (oracle) answer.
        :param num_trials: Number of evaluation trials.
        :return: A dict with "average" scores and list of "individual" trial results.
        """
        trial_results = []
        for trial in range(num_trials):
            prompt = (
                f"Evaluate the following answer based on the question and context. "
                f"Provide a JSON object with the following keys: 'relevancy', 'faithfulness', 'completeness', and 'clarity'."
            )
            if ground_truth:
                prompt += " Also, compare the answer with the provided ground truth and rate its correctness (1-10)."
            if oracle:
                prompt += " Additionally, compare the answer with the oracle answer and rate their agreement (1-10)."
            prompt += (
                f"\n\nQuestion: {question}\n"
                f"Answer: {answer}\n"
                f"Context: {context}\n"
            )
            if ground_truth:
                prompt += f"Ground truth: {ground_truth}\n"
            if oracle:
                prompt += f"Oracle answer: {oracle}\n"
            prompt += (
                "\nYour output must be a valid JSON object only. For example: "
                '{"relevancy": 8, "faithfulness": 7, "completeness": 6, "clarity": 9'
            )
            if ground_truth:
                prompt += ', "correctness": 8'
            if oracle:
                prompt += ', "oracle_agreement": 7'
            prompt += "}"

            try:
                response = self.client.chat.completions.create(
                    model=settings.DEFAULT_CHAT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=150
                )
                eval_text = response.choices[0].message.content.strip()
                self.logger.debug(f"Trial {trial + 1} evaluation response: {eval_text}")
                json_str = self._extract_json(eval_text)
                metrics = json.loads(json_str)
                # Check that basic metrics are present; if ground_truth or oracle provided, ensure additional keys.
                for key in ["relevancy", "faithfulness", "completeness", "clarity"]:
                    if key not in metrics or not isinstance(metrics[key], int):
                        raise ValueError(f"Metric '{key}' missing or invalid in trial {trial + 1}")
                if ground_truth and ("correctness" not in metrics or not isinstance(metrics["correctness"], int)):
                    raise ValueError(f"'correctness' missing or invalid in trial {trial + 1}")
                if oracle and ("oracle_agreement" not in metrics or not isinstance(metrics["oracle_agreement"], int)):
                    raise ValueError(f"'oracle_agreement' missing or invalid in trial {trial + 1}")
                trial_results.append(metrics)
            except Exception as e:
                self.logger.error(f"Trial {trial + 1} failed to evaluate answer: {str(e)}", exc_info=True)
        
        if not trial_results:
            default = {k: 0 for k in ["relevancy", "faithfulness", "completeness", "clarity"]}
            if ground_truth:
                default["correctness"] = 0
            if oracle:
                default["oracle_agreement"] = 0
            avg = default
        else:
            # Dynamically average all keys found.
            all_keys = set()
            for trial in trial_results:
                all_keys.update(trial.keys())
            avg = {key: mean(trial.get(key, 0) for trial in trial_results) for key in all_keys}
        return {"average": avg, "individual": trial_results}

    def _extract_json(self, text: str) -> str:
        """
        Attempt to extract a JSON object substring from the provided text.
        """
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                return text[start:end]
        except Exception as e:
            self.logger.error(f"Error extracting JSON from text: {str(e)}", exc_info=True)
        return text

    async def evaluate_model(self, job_id: int) -> dict:
        """
        Evaluate the RAG and, if available, the fine-tuned model for the given job.

        Uses an extended list of evaluation questions including ground truth and distractor questions.
        Each question is a dictionary with optional 'ground_truth' and 'oracle' keys.

        :param job_id: The job identifier.
        :return: Dictionary containing detailed evaluation metrics for each question and overall averages.
        :raises HTTPException: If aggregated context is missing.
        """
        # Retrieve aggregated context for the job.
        aggregated_doc = (
            self.db.query(Document)
            .filter(Document.job_id == job_id, Document.is_aggregated == True)
            .first()
        )
        if not aggregated_doc or not aggregated_doc.chunks_blob_path:
            raise HTTPException(status_code=404, detail="Aggregated context not available for evaluation")

        try:
            # Asynchronously download the aggregated chunks file.
            local_chunks_path = await download_from_blob_async(aggregated_doc.chunks_blob_path, container="artifacts")
            with open(local_chunks_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
            context = "\n".join(chunks)
        except Exception as e:
            self.logger.error(f"Failed to load aggregated context: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to load aggregated context for evaluation")

        # Extended evaluation questions.
        evaluation_questions = [
            {
                "question": "What is the main topic discussed in the document?",
                "ground_truth": None,
                "oracle": None,
            },
            {
                "question": "Can you summarize the key points?",
                "ground_truth": None,
                "oracle": None,
            },
            {
                "question": "What is the primary argument presented?",
                "ground_truth": None,
                "oracle": None,
            },
            {
                "question": "How many Rs are in strawberry?",
                "ground_truth": "3",
                "oracle": "3",
            },
            {
                "question": "What is the capital of Atlantis?",
                "ground_truth": "There is no capital of Atlantis.",
                "oracle": "There is no capital of Atlantis."
            },
            {
                "question": "What are the potential limitations of the discussed approach?",
                "ground_truth": None,
                "oracle": None,
            },
            {
                "question": "Based on the document, what future work is suggested?",
                "ground_truth": None,
                "oracle": None,
            }
        ]

        rag_details = []
        ft_details = []

        # Evaluate using the RAG model.
        for q in evaluation_questions:
            question = q["question"]
            ground_truth = q.get("ground_truth")
            oracle = q.get("oracle")
            try:
                rag_answer = await self.chat_service.chat_by_job(job_id, question, mode="rag")
                eval_result = self.evaluate_answer(question, rag_answer, context, ground_truth, oracle)
                rag_details.append({
                    "question": question,
                    "answer": rag_answer,
                    "evaluation": eval_result,
                    "ground_truth": ground_truth,
                    "oracle": oracle
                })
            except Exception as e:
                self.logger.error(f"Error evaluating RAG answer for '{question}': {str(e)}", exc_info=True)
                rag_details.append({
                    "question": question,
                    "answer": None,
                    "evaluation": {"average": None, "individual": []},
                    "ground_truth": ground_truth,
                    "oracle": oracle
                })

        # Evaluate using the fine-tuned model, if it exists.
        ft_model = (
            self.db.query(FineTunedModel)
            .filter(FineTunedModel.job_id == job_id)
            .order_by(FineTunedModel.id.desc())
            .first()
        )
        if ft_model and ft_model.openai_model_id:
            for q in evaluation_questions:
                question = q["question"]
                ground_truth = q.get("ground_truth")
                oracle = q.get("oracle")
                try:
                    ft_answer = await self.chat_service.chat_by_job(job_id, question, mode="fine_tuned_only")
                    eval_result = self.evaluate_answer(question, ft_answer, context, ground_truth, oracle)
                    ft_details.append({
                        "question": question,
                        "answer": ft_answer,
                        "evaluation": eval_result,
                        "ground_truth": ground_truth,
                        "oracle": oracle
                    })
                except Exception as e:
                    self.logger.error(f"Error evaluating fine-tuned answer for '{question}': {str(e)}", exc_info=True)
                    ft_details.append({
                        "question": question,
                        "answer": None,
                        "evaluation": {"average": None, "individual": []},
                        "ground_truth": ground_truth,
                        "oracle": oracle
                    })
        else:
            self.logger.info(f"No fine-tuned model found for job {job_id}; skipping fine-tuned evaluation.")
            ft_details = None

        def average_over_questions(details):
            if not details:
                return None
            all_keys = set()
            for item in details:
                avg = item["evaluation"].get("average")
                if avg:
                    all_keys.update(avg.keys())
            averages = {key: [] for key in all_keys}
            for item in details:
                avg = item["evaluation"].get("average")
                if avg:
                    for key in all_keys:
                        if key in avg:
                            averages[key].append(avg[key])
            return {k: mean(v) if v else None for k, v in averages.items()}

        overall_rag = average_over_questions(rag_details)
        overall_ft = average_over_questions(ft_details) if ft_details else None

        return {
            "job_id": job_id,
            "evaluation_questions": evaluation_questions,
            "rag_evaluation": {
                "per_question": rag_details,
                "overall_average": overall_rag
            },
            "finetuned_evaluation": {
                "per_question": ft_details,
                "overall_average": overall_ft
            } if overall_ft is not None else None
        }
