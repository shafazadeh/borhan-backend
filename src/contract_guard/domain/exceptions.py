class ContractFormatError(ValueError):
    """The uploaded document cannot be read safely."""


class RiskAnalysisError(Exception):
    """Risk analysis could not be completed."""
