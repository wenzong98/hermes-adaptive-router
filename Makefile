.PHONY: test lint fmt clean install

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests/ -q --tb=short

test-verbose:
	PYTHONPATH=src $(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m py_compile src/hermes_adaptive_router/*.py
	$(PYTHON) -m py_compile tests/*.py

fmt:
	@echo "Format not configured; add black/ruff if desired"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/
