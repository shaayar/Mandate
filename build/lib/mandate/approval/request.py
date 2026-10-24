from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ApprovalRequest:
    id: str
    tool_name: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]
    state: str = "pending"
    created_at: Any = None
    approved: bool = False

    def is_approved(self) -> bool:
        return self.approved

    def is_pending(self) -> bool:
        return self.state == "pending"

    def is_valid_for(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        return self.tool_name == tool_name and self.parameters == parameters