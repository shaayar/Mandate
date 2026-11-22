# Mandate Test Ownership Boundary

## Mandate-owned tests
These tests are standalone and do not depend on FRIDAY. They form the Mandate test baseline.

- `tests/test_stage1.py` - 59 acceptance tests (AC-001 through AC-050)
- `tests/test_approval_hardening.py` - 9 approval lifecycle tests
- **Total: 68 tests passing**

Run: `python -m pytest -q tests/test_stage1.py tests/test_approval_hardening.py`

## FRIDAY-owned integration tests
These tests exercise the FRIDAY-Mandate adapter integration. They import from `friday.integration.mandate_adapter` and should run inside the FRIDAY test environment.

- `tests/test_integration_adapter.py` - 10 test classes:
  - `TestAllowExecution`
  - `TestDenyBlocksExecution`
  - `TestRequireApprovalBlocksWithoutValidApproval`
  - `TestApprovalSingleUse`
  - `TestApprovalMismatchedParameters`
  - `TestApprovalToolNameMismatch`
  - `TestAuditEmissionFailureBlocks`
  - `TestPolicyEvaluationFailureBlocks`
  - `TestConsumedApprovalNotRestored`
  - `TestAllProtectedDispatchPaths`

These tests were preserved in the Mandate repository and require the `friday` package. When FRIDAY is not available, the test file contains a top-level import guard that causes pytest to raise an import error. A `pytest.ini` configuration excludes this file from the default `python -m pytest -q` run; the integration suite must be run with explicit inclusion or inside the FRIDAY environment.

Run (with FRIDAY): `python -m pytest -q tests/test_integration_adapter.py`

**Note**: The `friday` package is not installed in the current environment. The integration test file is preserved in Mandate and will be executed when FRIDAY is available.

## Test execution baseline

- `python -m pytest -q` — 68 passed (Mandate-owned tests only; integration test file excluded via `pytest.ini`)
- `python -m pytest -q tests/test_stage1.py tests/test_approval_hardening.py` — 68 passed
- `python -m pytest -q tests/test_integration_adapter.py` — requires FRIDAY package
- `python -m pytest -q` — 68 passed (full command, no FRIDAY import error; integration file excluded)