.PHONY: install lint format test check

PYTHON := venv/bin/python

install:
	$(PYTHON) -m pip install -e ".[dev,ingest,knowledge]"

lint:
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m black --check src/ tests/

format:
	$(PYTHON) -m ruff check src/ tests/ --fix
	$(PYTHON) -m black src/ tests/

test:
	$(PYTHON) -m pytest -q

check: lint test
