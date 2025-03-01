from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict

class APIResponse(BaseModel):
    """
    Standard API response schema.

    Attributes:
      data (Optional[Any]): The data payload of the response.
      errorMessage (Optional[str]): Error message if the request failed.
      success (bool): Indicates whether the request was successful.
      errors (List[str]): A list of error messages (if any).

    Sample JSON (response from chat.py):
    {
        "data": "Based on the provided context, the answer to your question is: [sample answer].",
        "errorMessage": "",
        "success": true,
        "errors": []
    }
    """
    model_config = ConfigDict(extra="forbid")
    data: Optional[Any] = None
    errorMessage: Optional[str] = ""
    success: bool = True
    errors: List[str] = []
