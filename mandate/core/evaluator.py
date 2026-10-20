from mandate.core.types import Decision, PolicyRule


def _tool_name_matches(tool_name: str, condition_tool_name: str) -> bool:
    """Check if a tool name matches a condition's tool_name.

    Supports exact matching and the universal wildcard '*'.
    """
    if condition_tool_name == "*":
        return True
    return tool_name == condition_tool_name


def _eval_parameter_operator(
    actual_value: Any,
    condition: Dict[str, Any],
) -> bool:
    """Evaluate a single parameter condition using the specified operator."""
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


def _condition_matches(
    condition: Dict[str, Any],
    tool_name: str,
    parameters: Dict[str, Any],
) -> bool:
    """Check if all conditions in a rule condition match the given tool call.

    Returns True only if tool_name matches AND all parameter conditions match
    (AND semantics - all present parameters must match).
    """
    # Check tool_name match
    if "tool_name" in condition:
        condition_tool_name = condition["tool_name"]
        if not _tool_name_matches(tool_name, condition_tool_name):
            return False

    # Check parameter conditions
    if "parameters" in condition:
        param_conditions = condition["parameters"]
        for param_name, param_condition in param_conditions.items():
            if param_name not in parameters:
                # Parameter is absent from the tool call;
                # if the rule has a condition for this parameter, it doesn't match
                # unless the parameter is optional. Per the design, all parameters
                # in the condition must be satisfied.
                return False
            if not _eval_parameter_operator(parameters[param_name], param_condition):
                return False

    return True


def evaluate_policy_rules(
    rules: List[PolicyRule],
    tool_name: str,
    parameters: Dict[str, Any],
) -> Decision:
    """Evaluate a list of policy rules (first-match within a single file).

    Returns the decision of the first matching rule, or DENY if no rule matches.
    """
    for rule in rules:
        if rule.condition.get("tool_name") is not None and _condition_matches(
            rule.condition, tool_name, parameters
        ):
            return rule.action
        elif "tool_name" not in rule.condition:
            # Rule has no tool_name condition; match on parameters only
            # But this is unusual; let's check parameter conditions only
            matched = True
            if "parameters" in rule.condition:
                param_conditions = rule.condition["parameters"]
                for param_name, param_condition in param_conditions.items():
                    if param_name not in parameters:
                        matched = False
                        break
                    if not _eval_parameter_operator(parameters[param_name], param_condition):
                        matched = False
                        break
                if not matched:
                    continue
            # If we get here, tool_name either doesn't matter or matches
            # (no tool_name condition or wildcard)
            # Check tool_name explicitly
            if "tool_name" in rule.condition:
                if not _tool_name_matches(tool_name, rule.condition["tool_name"]):
                    continue
            return rule.action

    return Decision.DENY


def evaluate_policy_set(
    policies: "PolicySet",
    tool_name: str,
    parameters: Dict[str, Any],
) -> Decision:
    """Evaluate a PolicySet with full precedence algorithm.

    Precedence order: DENY > REQUIRE_APPROVAL > ALLOW
    Within each file: first-match wins.
    Across files: later-loaded files have higher precedence.
    Default-deny if no rule matches.
    """
    # Phase 1: Find the latest file with a matching DENY rule (first-match within file)
    winning_deny = None  # (policy_index, rule_index)
    for pi in range(len(policies.policies) - 1, -1, -1):
        policy = policies.policies[pi]
        for ri, rule in enumerate(policy.rules):
            if rule.action == Decision.DENY and _condition_matches(
                rule.condition, tool_name, parameters
            ):
                winning_deny = (pi, ri)
                break  # first match within this file
        if winning_deny is not None:
            break  # since we iterate reverse, this is the highest-precedence file with DENY

    if winning_deny is not None:
        pi, ri = winning_deny
        return policies.policies[pi].rules[ri].action

    # Phase 2: Find the latest file with a matching REQUIRE_APPROVAL rule (first-match within file)
    winning_reqapp = None
    for pi in range(len(policies.policies) - 1, -1, -1):
        policy = policies.policies[pi]
        for ri, rule in enumerate(policy.rules):
            if rule.action == Decision.REQUIRE_APPROVAL and _condition_matches(
                rule.condition, tool_name, parameters
            ):
                winning_reqapp = (pi, ri)
                break
        if winning_reqapp is not None:
            break

    if winning_reqapp is not None:
        pi, ri = winning_reqapp
        return policies.policies[pi].rules[ri].action

    # Phase 3: Find the latest file with a matching ALLOW rule (first-match within file)
    winning_allow = None
    for pi in range(len(policies.policies) - 1, -1, -1):
        policy = policies.policies[pi]
        for ri, rule in enumerate(policy.rules):
            if rule.action == Decision.ALLOW and _condition_matches(
                rule.condition, tool_name, parameters
            ):
                winning_allow = (pi, ri)
                break
        if winning_allow is not None:
            break

    if winning_allow is not None:
        pi, ri = winning_allow
        return policies.policies[pi].rules[ri].action

    # Phase 4: Default-deny
    return Decision.DENY