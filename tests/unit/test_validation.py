"""Tests for shadowlink.common.validation and exception hierarchy.

Covers:
- validate_no_forbidden_columns  (column-name guard)
- validate_no_duplicate_columns
- validate_has_columns
- validate_hashable_values
- Exception hierarchy (ShadowlinkError base)
- Signature inspection: no public function may have a forbidden parameter name
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pandas as pd
import pytest

from shadowlink.common.exceptions import (
    ConfigError,
    DatasetLoadError,
    ShadowlinkError,
    ValidationError,
)
from shadowlink.common.validation import (
    FORBIDDEN_COLUMN_NAMES,
    FORBIDDEN_PARAM_NAMES,
    validate_has_columns,
    validate_hashable_values,
    validate_no_duplicate_columns,
    validate_no_forbidden_columns,
)

# ===========================================================================
# Exception hierarchy
# ===========================================================================


class TestExceptionHierarchy:
    """All custom exceptions must derive from ShadowlinkError."""

    def test_shadowlink_error_is_exception(self) -> None:
        err = ShadowlinkError("base")
        assert isinstance(err, Exception)

    def test_validation_error_is_shadowlink_error(self) -> None:
        err = ValidationError("v")
        assert isinstance(err, ShadowlinkError)

    def test_dataset_load_error_is_shadowlink_error(self) -> None:
        err = DatasetLoadError("d")
        assert isinstance(err, ShadowlinkError)

    def test_config_error_is_shadowlink_error(self) -> None:
        err = ConfigError("c")
        assert isinstance(err, ShadowlinkError)

    def test_validation_error_carries_message(self) -> None:
        msg = "some actionable message"
        err = ValidationError(msg)
        assert msg in str(err)

    def test_dataset_load_error_carries_message(self) -> None:
        msg = "file not found: /tmp/x.csv"
        err = DatasetLoadError(msg)
        assert msg in str(err)

    def test_config_error_carries_message(self) -> None:
        msg = "bin_width must be > 0"
        err = ConfigError(msg)
        assert msg in str(err)

    def test_shadowlink_error_can_be_caught_as_exception(self) -> None:
        with pytest.raises(Exception):
            raise ValidationError("test catch")

    def test_validation_error_not_dataset_load_error(self) -> None:
        """Subclasses are independent of each other."""
        err = ValidationError("v")
        assert not isinstance(err, DatasetLoadError)

    def test_dataset_load_error_not_config_error(self) -> None:
        err = DatasetLoadError("d")
        assert not isinstance(err, ConfigError)


# ===========================================================================
# validate_no_forbidden_columns
# ===========================================================================


class TestValidateNoForbiddenColumns:
    """Column-name guard: raise ValidationError on forbidden column names."""

    # --- happy path --------------------------------------------------------

    def test_clean_dataframe_does_not_raise(self) -> None:
        df = pd.DataFrame({"age": [1, 2], "city": ["A", "B"]})
        validate_no_forbidden_columns(df)  # must not raise

    def test_empty_dataframe_does_not_raise(self) -> None:
        validate_no_forbidden_columns(pd.DataFrame())

    def test_empty_rows_does_not_raise(self) -> None:
        df = pd.DataFrame({"age": pd.Series([], dtype=int)})
        validate_no_forbidden_columns(df)

    # --- individual forbidden names (exact case) ---------------------------

    def test_ground_truth_exact_raises(self) -> None:
        df = pd.DataFrame({"ground_truth": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_true_id_exact_raises(self) -> None:
        df = pd.DataFrame({"true_id": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_true_identity_exact_raises(self) -> None:
        df = pd.DataFrame({"true_identity": ["A"]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_identity_key_exact_raises(self) -> None:
        df = pd.DataFrame({"identity_key": [99]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    # --- case-insensitivity ------------------------------------------------

    def test_ground_truth_uppercase_raises(self) -> None:
        df = pd.DataFrame({"GROUND_TRUTH": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_ground_truth_mixed_case_raises(self) -> None:
        df = pd.DataFrame({"Ground_Truth": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_true_id_uppercase_raises(self) -> None:
        df = pd.DataFrame({"TRUE_ID": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_identity_key_mixed_case_raises(self) -> None:
        df = pd.DataFrame({"Identity_Key": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    # --- whitespace in column name -----------------------------------------

    def test_ground_truth_with_leading_space_raises(self) -> None:
        # Strip is applied before comparison.
        df = pd.DataFrame({" ground_truth": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    def test_ground_truth_with_trailing_space_raises(self) -> None:
        df = pd.DataFrame({"ground_truth ": [1]})
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)

    # --- actionable error message ------------------------------------------

    def test_error_message_names_the_violation(self) -> None:
        df = pd.DataFrame({"ground_truth": [1]})
        with pytest.raises(ValidationError) as exc_info:
            validate_no_forbidden_columns(df)
        msg = str(exc_info.value).lower()
        assert "ground_truth" in msg

    def test_error_message_tells_caller_to_remove_column(self) -> None:
        df = pd.DataFrame({"true_id": [1]})
        with pytest.raises(ValidationError) as exc_info:
            validate_no_forbidden_columns(df)
        assert "Remove" in str(exc_info.value) or "remove" in str(exc_info.value)

    def test_error_message_lists_multiple_violations(self) -> None:
        df = pd.DataFrame({"ground_truth": [1], "true_id": [2], "age": [3]})
        with pytest.raises(ValidationError) as exc_info:
            validate_no_forbidden_columns(df)
        msg = str(exc_info.value)
        assert "ground_truth" in msg
        assert "true_id" in msg

    # --- FORBIDDEN_COLUMN_NAMES constant coverage -------------------------

    def test_forbidden_names_set_contains_all_four(self) -> None:
        assert "ground_truth" in FORBIDDEN_COLUMN_NAMES
        assert "true_id" in FORBIDDEN_COLUMN_NAMES
        assert "true_identity" in FORBIDDEN_COLUMN_NAMES
        assert "identity_key" in FORBIDDEN_COLUMN_NAMES

    def test_forbidden_names_exactly_four(self) -> None:
        assert len(FORBIDDEN_COLUMN_NAMES) == 4

    def test_forbidden_param_names_matches_column_names(self) -> None:
        """FORBIDDEN_PARAM_NAMES must equal FORBIDDEN_COLUMN_NAMES."""
        assert FORBIDDEN_PARAM_NAMES == FORBIDDEN_COLUMN_NAMES

    # --- original DataFrame not modified -----------------------------------

    def test_input_dataframe_not_mutated_on_pass(self) -> None:
        df = pd.DataFrame({"age": [1, 2]})
        df_copy = df.copy()
        validate_no_forbidden_columns(df)
        pd.testing.assert_frame_equal(df, df_copy)

    def test_input_dataframe_not_mutated_on_raise(self) -> None:
        df = pd.DataFrame({"ground_truth": [1], "age": [2]})
        df_copy = df.copy()
        with pytest.raises(ValidationError):
            validate_no_forbidden_columns(df)
        pd.testing.assert_frame_equal(df, df_copy)


# ===========================================================================
# validate_no_duplicate_columns
# ===========================================================================


class TestValidateNoDuplicateColumns:
    def test_unique_columns_pass(self) -> None:
        df = pd.DataFrame([[1, 2]], columns=["a", "b"])
        validate_no_duplicate_columns(df)

    def test_duplicate_column_raises(self) -> None:
        df = pd.DataFrame([[1, 2]], columns=["a", "a"])
        with pytest.raises(ValidationError, match="duplicate"):
            validate_no_duplicate_columns(df)

    def test_error_names_the_duplicate(self) -> None:
        df = pd.DataFrame([[1, 2]], columns=["age", "age"])
        with pytest.raises(ValidationError) as exc_info:
            validate_no_duplicate_columns(df)
        assert "age" in str(exc_info.value)

    def test_empty_dataframe_passes(self) -> None:
        validate_no_duplicate_columns(pd.DataFrame())


# ===========================================================================
# validate_has_columns
# ===========================================================================


class TestValidateHasColumns:
    def test_nonempty_df_passes(self) -> None:
        df = pd.DataFrame({"x": [1]})
        validate_has_columns(df)

    def test_zero_column_df_raises(self) -> None:
        with pytest.raises(ValidationError):
            validate_has_columns(pd.DataFrame())

    def test_error_is_actionable(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_has_columns(pd.DataFrame())
        assert "zero columns" in str(exc_info.value).lower()


# ===========================================================================
# validate_hashable_values
# ===========================================================================


class TestValidateHashableValues:
    def test_all_scalar_values_pass(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        validate_hashable_values(df)

    def test_list_cell_raises(self) -> None:
        df = pd.DataFrame({"a": [[1, 2], [3, 4]]})
        with pytest.raises(ValidationError):
            validate_hashable_values(df)

    def test_error_names_the_column(self) -> None:
        df = pd.DataFrame({"bad_col": [{"k": "v"}]})
        with pytest.raises(ValidationError) as exc_info:
            validate_hashable_values(df)
        assert "bad_col" in str(exc_info.value)


# ===========================================================================
# Signature inspection — no public function may carry a forbidden param name
# ===========================================================================


class TestPublicFunctionSignatures:
    """Walk the entire shadowlink package and check every public callable.

    A public callable is any function or method whose name does not start
    with an underscore and whose ``__module__`` starts with ``"shadowlink"``.

    ``self`` and ``cls`` are excluded from the parameter check since they
    are conventional receiver names, not caller-supplied arguments.
    """

    _FORBIDDEN: frozenset[str] = FORBIDDEN_PARAM_NAMES

    def _collect_public_callables(
        self,
    ) -> list[tuple[str, inspect.Signature]]:
        """Return (qualified_name, signature) for every public callable."""
        import shadowlink

        results: list[tuple[str, inspect.Signature]] = []

        def _from_module(module: object) -> None:
            # Stand-alone functions
            for fname, func in inspect.getmembers(module, inspect.isfunction):
                if fname.startswith("_"):
                    continue
                mod_name: str = getattr(func, "__module__", "") or ""
                if not mod_name.startswith("shadowlink"):
                    continue
                try:
                    sig = inspect.signature(func)
                    results.append((f"{mod_name}.{fname}", sig))
                except (ValueError, TypeError):
                    pass

            # Methods from classes defined in shadowlink
            for cname, cls in inspect.getmembers(module, inspect.isclass):
                if cname.startswith("_"):
                    continue
                cls_mod: str = getattr(cls, "__module__", "") or ""
                if not cls_mod.startswith("shadowlink"):
                    continue
                for mname, method in inspect.getmembers(
                    cls, predicate=inspect.isfunction
                ):
                    if mname.startswith("_"):
                        continue
                    try:
                        sig = inspect.signature(method)
                        results.append((f"{cls_mod}.{cname}.{mname}", sig))
                    except (ValueError, TypeError):
                        pass

        _from_module(shadowlink)
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            path=shadowlink.__path__,  # type: ignore[attr-defined]
            prefix="shadowlink.",
            onerror=lambda _x: None,
        ):
            try:
                mod = importlib.import_module(modname)
                _from_module(mod)
            except Exception:
                pass

        return results

    def test_no_forbidden_parameter_names_in_public_functions(self) -> None:
        """Every public function/method must avoid forbidden parameter names.

        'self' and 'cls' are excluded because they are receiver conventions,
        not caller-supplied arguments.
        """
        callables = self._collect_public_callables()
        # Ensure we actually found some callables (guard against silent failure)
        assert len(callables) >= 1, (
            "Signature scan found zero public callables in shadowlink — "
            "check that the package is importable."
        )

        skip_params = {"self", "cls"}
        violations: list[str] = []
        for qual_name, sig in callables:
            for param_name in sig.parameters:
                if param_name in skip_params:
                    continue
                if param_name.lower() in self._FORBIDDEN:
                    violations.append(f"{qual_name}(..., {param_name}, ...)")

        assert violations == [], (
            "Found forbidden parameter name(s) in public functions:\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\n\nSHADOWLINK public APIs must never accept ground-truth identity "
            "parameters.  Rename or remove these parameters."
        )
