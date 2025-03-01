import logging
import json
import random
from openai import OpenAI
from app.config import settings
from app.utils.blob_storage import upload_to_blob_async

logger = logging.getLogger(__name__)

class SyntheticDataGenerator:
    """
    Service for generating synthetic JSONL training data for fine-tuning.

    This service uses an OpenAI chat completion call to generate at least 10 valid
    JSONL examples based on input text (derived from document chunks). If the primary
    attempt fails (after a given number of attempts), a fallback method using pre-defined
    templates is used instead.

    The raw responses (both primary and fallback) are logged to blob storage if a job_id is provided.
    """
    def __init__(self, client: OpenAI = None) -> None:
        """
        Initialize the SyntheticDataGenerator.

        :param client: An instance of the OpenAI client. If not provided, a new client is created using the API key from settings.
        """
        self.client = client or OpenAI(api_key=settings.OPENAI_API_KEY)
        self.logger = logger

    async def generate_synthetic_jsonl(self, chunks, max_attempts: int = 3, job_id: int = None) -> str:
        """
        Asynchronously generate synthetic JSONL data using an OpenAI model.
        
        The function constructs a prompt based on the input text (aggregated from chunks)
        and calls the OpenAI chat completion API. If the response doesn't contain at least 10 lines
        of valid JSON, the function will retry (up to max_attempts). If all attempts fail, it falls back
        to a fallback method.

        :param chunks: List of text chunks.
        :param max_attempts: Maximum number of attempts to generate valid JSONL.
        :param job_id: Optional job ID to log the raw responses.
        :return: A string containing synthetic JSONL data (each line is a valid JSON object).
        :raises Exception: If generation fails and fallback also fails.
        """
        # Combine chunks into input text.
        input_text = "\n".join(chunk.strip() for chunk in chunks if chunk.strip()) if chunks else ""
        if not input_text:
            self.logger.warning("No valid chunks provided; using generic fallback text")
            input_text = "Generic financial data: creditor details and personal info."

        # Construct the prompt.
        prompt = f"""You are a highly intelligent assistant tasked with generating synthetic training data for fine-tuning a chatbot. Given the following input text, create at least 15 distinct chat-style examples in JSONL format, one JSON object per line. Each JSON object must have the following structure:
{{
    "messages": [
         {{"role": "system", "content": "You are a factual assistant that provides accurate answers."}},
         {{"role": "user", "content": <user message>}},
         {{"role": "assistant", "content": <assistant message>}}
    ]
}}
Ensure that:
- The user message is a creative variation derived from the input text (e.g., "What does this describe?", "Can you explain this?", "Summarize this:" etc.).
- The assistant message is a factual, concise answer based on the input text.
- There is no additional text, markdown formatting, or explanation outside of the JSON objects.
- Each line is a valid JSON object.

Input text:
{input_text}
"""
        attempts = 0
        while attempts < max_attempts:
            try:
                response = self.client.chat.completions.create(
                    model=settings.DEFAULT_CHAT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=5000
                )
                raw_response = response.choices[0].message.content.strip()
                self.logger.debug("GPT raw response: %s", raw_response)
                await self._log_response(job_id, raw_response, primary=True)

                jsonl_output = self._remove_markdown_fences(raw_response)
                lines = [line for line in jsonl_output.splitlines() if line.strip()]
                if len(lines) < 10:
                    raise ValueError(f"Expected at least 10 lines, but got {len(lines)}.")

                valid_lines = []
                for i, line in enumerate(lines):
                    try:
                        # Validate JSON for each line.
                        obj = json.loads(line)
                        valid_lines.append(json.dumps(obj))
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON on line {i+1}: {line} - {str(e)}")

                self.logger.debug("Successfully generated valid JSONL data with %d lines.", len(valid_lines))
                return "\n".join(valid_lines)
            except Exception as e:
                attempts += 1
                self.logger.error("Attempt %d failed: %s", attempts, str(e), exc_info=True)
                if attempts >= max_attempts:
                    self.logger.warning("Max attempts reached. Using fallback method for JSONL generation.")
                    fallback_output = self.generate_fallback_jsonl(input_text, min_examples=10)
                    await self._log_response(job_id, fallback_output, primary=False)
                    return fallback_output

    def _remove_markdown_fences(self, text: str) -> str:
        """
        Remove markdown code fences from text, if present.
        
        :param text: The input text.
        :return: Cleaned text without markdown fences.
        """
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines)
        return text

    async def _log_response(self, job_id, response_text: str, primary: bool = True):
        """
        Asynchronously log the raw GPT response to blob storage if a job_id is provided.
        
        :param job_id: The job ID.
        :param response_text: The raw response text.
        :param primary: Flag indicating whether this is the primary response.
        """
        if job_id is not None:
            try:
                suffix = "raw_response.txt" if primary else "fallback_raw_response.txt"
                log_blob_path = await upload_to_blob_async(
                    response_text.encode("utf-8"),
                    f"synthetic_logs/job-{job_id}/{suffix}",
                    container="logs"
                )
                self.logger.info("Logged %s synthetic JSONL response to %s", "primary" if primary else "fallback", log_blob_path)
            except Exception as log_err:
                self.logger.error("Failed to log %s synthetic response for job %s: %s", "primary" if primary else "fallback", job_id, str(log_err))

    def generate_fallback_jsonl(self, input_text: str, min_examples: int = 10) -> str:
        """
        Generate fallback synthetic JSONL data using pre-defined templates.
        
        :param input_text: The input text to base the examples on.
        :param min_examples: Minimum number of examples to generate.
        :return: A string containing fallback synthetic JSONL data.
        """
        fallback_templates = [
            {
                "messages": [
                    {"role": "system", "content": "You are a factual assistant that provides accurate answers."},
                    {"role": "user", "content": "Please explain the following data: {input_text}"},
                    {"role": "assistant", "content": "Based on the data, it appears that {summary}."}
                ]
            },
            {
                "messages": [
                    {"role": "system", "content": "You are a helpful and knowledgeable assistant."},
                    {"role": "user", "content": "What does the following information mean? {input_text}"},
                    {"role": "assistant", "content": "This information suggests that {summary}."}
                ]
            },
            {
                "messages": [
                    {"role": "system", "content": "You are a factual assistant."},
                    {"role": "user", "content": "Summarize this data: {input_text}"},
                    {"role": "assistant", "content": "In summary, {summary}."}
                ]
            }
        ]
        
        fallback_lines = []
        summary = input_text if len(input_text) <= 50 else input_text[:50] + "..."
        for _ in range(min_examples):
            template = random.choice(fallback_templates)
            filled_template = {
                "messages": [
                    {"role": msg["role"], "content": msg["content"].format(input_text=input_text, summary=summary)}
                    for msg in template["messages"]
                ]
            }
            fallback_lines.append(json.dumps(filled_template))
        
        # Validate that each generated line is valid JSON.
        for line in fallback_lines:
            json.loads(line)
        
        return "\n".join(fallback_lines)
