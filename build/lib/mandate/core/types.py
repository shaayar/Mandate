from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


class Decision(Enum):
    ALLOW = auto()
    DENY = auto()
    REQUIRE_APPROVAL = auto()


class ComparisonOperator(Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    CONTAINS = "contains"
    REGEX = "regex"


ALLOW = Decision.ALLOW
DENY = Decision.DENY
REQUIRE_APPROVAL = Decision.REQUIRE_APPROVAL

Pattern = str


@dataclass
class EvaluationContext:
    tool_name: str
    parameters: Dict[str, Any]
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class PolicyRule:
    name: str
    action: Decision
    condition: Dict[str, Any]

    def matches(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        if "tool_name" in self.condition:
            tn_condition = self.condition["tool_name"]
            if tn_condition == "*":
                pass
            elif tn_condition != tool_name:
                return False

        if "parameters" in self.condition:
            param_conditions = self.condition["parameters"]
            for param_name, param_condition in param_conditions.items():
                if param_name not in parameters:
                    return False
                if not self._eval_parameter(param_name, parameters[param_name], param_condition):
                    return False

        return True

    def _eval_parameter(self, param_name: str, actual_value: Any, condition: Dict[str, Any]) -> bool:
        operator = condition.get("operator")
        value = condition.get("value")

        if operator is None or value is None:
            return False

        op = operator
        if op == "eq":
            return actual_value == value
        elif op == "neq":
            return actual_value != value
        elif op == "gt":
            return actual_value > value
        elif op == "lt":
            return actual_value < value
        elif op == "gte":
            return actual_value >= value
        elif op == "lte":
            return actual_value <= value
        elif op == "contains":
            return str(value) in str(actual_value)
        elif op == "regex":
            import re
            return bool(re.search(str(value), str(actual_value)))
        else:
            return False