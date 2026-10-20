class MandateError(Exception):
    """Base exception for all mandate-related errors."""

    pass


class PolicyValidationError(MandateError):
    """Raised when a policy definition is invalid on load."""

    pass


class PolicyEvaluationError(MandateError):
    """Raised when policy evaluation fails unexpectedly."""

    pass


class ApprovalUnavailableError(MandateError):
    """Raised when the approval mechanism is unavailable."""

    pass


class ApprovalAlreadyConsumedError(MandateError):
    """Raised when attempting to consume an already-consumed approval ID."""

    pass