# Contributing

TeXDelta welcomes focused bug reports, fixtures, documentation, and patches.

1. Open an issue before starting a compatibility-surface or architecture change.
2. Use synthetic, redistributable fixtures. Never submit manuscripts, private review files, credentials, or third-party figures.
3. Install development dependencies with `python -m pip install -e '.[dev]'`.
4. Run `ruff check .`, `ruff format --check .`, `mypy src/texdelta`, and `pytest`.
5. Add or update tests for observable behavior and keep the report schema backward compatible.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Contributions are accepted under the MIT License.
