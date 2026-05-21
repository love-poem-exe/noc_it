from pydantic import BaseModel
from typing import Any, Optional


class ScriptRequest(BaseModel):
    script: str
    method: str
    payload: Optional[dict[str, Any]] = None
