# Make config
.SILENT:
MAKEFLAGS += --no-print-directory

# Code quality
.PHONY: lint test check coverage
lint:
	ruff check --fix
	ruff format
	mypy

test:
	pytest -v \
		--cov=fastapi_error_map \
		--cov-report=term-missing

check: lint test

coverage: check
	coverage html

# Project structure visualization
.PHONY: pycache-del
pycache-del:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +; \
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
