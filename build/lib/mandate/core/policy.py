import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from mandate.core.types import Decision, ComparisonOperator, PolicyRule, Pattern
from mandate.exceptions import PolicyValidationError


SUPPORTED_OPERATORS = {
    "eq",
    "neq",
    "gt",
    "lt",
    "gte",
    "lte",
    "contains",
    "regex",
}


class Policy:
    """A validated policy loaded from YAML or JSON."""

    def __init__(self, rules: List[PolicyRule] = None):
        self.rules = rules if rules is not None else []

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "Policy":
        path = Path(path)
        if not path.exists():
            raise PolicyValidationError(f"Policy file not found: {path}")
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PolicyValidationError(f"Malformed YAML in {path}: {e}")
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "Policy":
        path = Path(path)
        if not path.exists():
            raise PolicyValidationError(f"Policy file not found: {path}")
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PolicyValidationError(f"Malformed JSON in {path}: {e}")
        return cls.from_dict(data)

    @classmethod
    def from_yaml_string(cls, string: str) -> "Policy":
        try:
            data = yaml.safe_load(string)
        except yaml.YAMLError as e:
            raise PolicyValidationError(f"Malformed YAML string: {e}")
        return cls.from_dict(data)

    @classmethod
    def from_json_string(cls, string: str) -> "Policy":
        try:
            data = json.loads(string)
        except json.JSONDecodeError as e:
            raise PolicyValidationError(f"Malformed JSON string: {e}")
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        validated = cls._validate(data)
        rules = []
        for rule_data in validated.get("rules", []):
            rule = cls._validate_rule(rule_data)
            rules.append(rule)
        return cls(rules=rules)

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise PolicyValidationError("Policy must be a dictionary")

        if "rules" not in data:
            raise PolicyValidationError("Policy missing required 'rules' field")

        rules = data["rules"]
        if not isinstance(rules, list):
            raise PolicyValidationError("Policy 'rules' must be a list")

        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise PolicyValidationError(f"Rule {i} must be a dictionary")

        return data

    @staticmethod
    def _validate_rule(rule_data: Dict[str, Any]) -> PolicyRule:
        # Validate name
        if "name" not in rule_data:
            raise PolicyValidationError("Rule missing required 'name' field")
        name = rule_data["name"]
        if not isinstance(name, str):
            raise PolicyValidationError("Rule 'name' must be a string")

        # Validate action
        if "action" not in rule_data:
            raise PolicyValidationError("Rule missing required 'action' field")
        action_str = rule_data["action"]
        if action_str not in ("allow", "deny", "require_approval"):
            raise PolicyValidationError(
                f"Rule 'action' must be one of: allow, deny, require_approval; got '{action_str}'"
            )
        action = Decision[action_str.upper()]

        # Validate condition
        if "condition" not in rule_data:
            raise PolicyValidationError("Rule missing required 'condition' field")
        condition = rule_data["condition"]
        if not isinstance(condition, dict):
            raise PolicyValidationError("Rule 'condition' must be a dictionary")

        # Validate tool_name in condition
        if "tool_name" not in condition:
            raise PolicyValidationError("Rule condition missing required 'tool_name' field")
        tool_name = condition["tool_name"]
        if not isinstance(tool_name, str):
            raise PolicyValidationError("Rule condition 'tool_name' must be a string")
        if tool_name != "*" and not isinstance(tool_name, str):
            raise PolicyValidationError("Rule condition 'tool_name' must be a string or '*'")

        # Validate parameters in condition
        if "parameters" in condition:
            params = condition["parameters"]
            if not isinstance(params, dict):
                raise PolicyValidationError("Rule condition 'parameters' must be a dictionary")
            for param_name, param_condition in params.items():
                if not isinstance(param_condition, dict):
                    raise PolicyValidationError(
                        f"Rule condition parameter '{param_name}' must be a dictionary"
                    )
                if "operator" not in param_condition:
                    raise PolicyValidationError(
                        f"Rule condition parameter '{param_name}' missing 'operator' field"
                    )
                operator = param_condition["operator"]
                if operator not in SUPPORTED_OPERATORS:
                    raise PolicyValidationError(
                        f"Rule condition parameter '{param_name}' has unsupported operator '{operator}'. "
                        f"Supported operators: {', '.join(sorted(SUPPORTED_OPERATORS))}"
                    )
                if "value" not in param_condition:
                    raise PolicyValidationError(
                        f"Rule condition parameter '{param_name}' missing 'value' field"
                    )

        return PolicyRule(
            name=name,
            action=action,
            condition=condition,
        )

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> "Policy":
        """Load policy from file path, auto-detecting YAML or JSON format."""
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            return cls.from_yaml(path)
        elif suffix in (".json",):
            return cls.from_json(path)
        else:
            # Try YAML first, then JSON
            try:
                return cls.from_yaml(path)
            except PolicyValidationError:
                return cls.from_json(path)