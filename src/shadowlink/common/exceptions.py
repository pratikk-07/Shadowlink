"""Custom exception hierarchy for the SHADOWLINK platform.

All SHADOWLINK exceptions inherit from ``ShadowlinkError`` so callers can
catch the entire family with a single ``except ShadowlinkError``, or catch
specific sub-types for finer-grained handling.

Exception classes
-----------------
ShadowlinkError
    Base class. Never raise this directly; raise a sub-type.

ValidationError
    Raised when input data or configuration fails a defensive check
    (forbidden column names, unsupported types, bad parameter values, etc.).
    Messages must be actionable: tell the caller what is wrong and how to fix it.

DatasetLoadError
    Raised when a dataset file cannot be opened, read, or parsed.
    Messages include the file path and the underlying cause.

ConfigError
    Raised when a configuration value is semantically invalid even if it is
    syntactically correct (e.g. bin_width <= 0, unknown missing_policy string).
"""


class ShadowlinkError(Exception):
    """Base exception for all SHADOWLINK errors.

    Do not raise this class directly.  Use a specific subclass so callers
    can distinguish error categories.
    """


class ValidationError(ShadowlinkError):
    """Raised when input data or configuration fails validation.

    Examples
    --------
    - Input DataFrame contains a forbidden column (ground_truth, true_id …).
    - DataFrame has zero columns or duplicate column names.
    - A parameter value is outside its legal range.
    - An unhashable cell value prevents grouping.
    """


class DatasetLoadError(ShadowlinkError):
    """Raised when a dataset cannot be loaded from disk.

    Examples
    --------
    - File does not exist.
    - File is not readable.
    - File is empty (zero bytes or no rows after the header).
    - File cannot be parsed as CSV.
    """


class ConfigError(ShadowlinkError):
    """Raised when a configuration value is semantically invalid.

    Examples
    --------
    - ``bin_width`` is zero or negative.
    - ``missing_policy`` is not one of the recognised string literals.
    - A transformation spec references an unknown transformation kind.
    """
