# Contributing Guide

## Development Setup

```bash
git clone https://github.com/wenzong98/hermes-adaptive-router.git
cd hermes-adaptive-router
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
make test

# With coverage
pytest tests/ --cov=src/hermes_adaptive_router --cov-report=term-missing

# Specific test file
pytest tests/test_benchmark.py -v
```

## Adding a New Signal

1. Add keyword to `_DEFAULT_*_KEYWORDS` in `src/hermes_adaptive_router/router.py`
2. Add test case to `tests/test_benchmark.py`
3. Run `make test` to verify no regressions

## Adding a New Provider

1. Extend `ProviderPreference` in `src/hermes_adaptive_router/multi_provider.py`
2. Add detection logic in `classify_provider()`
3. Update `docs/API_REFERENCE.md`
4. Add benchmark cases

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings for public functions
- Keep deterministic — no LLM calls in core router

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request
