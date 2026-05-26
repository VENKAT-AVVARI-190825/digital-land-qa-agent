.PHONY: install dev test lint demo clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check digital_land_qa_agent tests

demo:
	python -m digital_land_qa_agent run --target pyspark-jobs --goal "Generate unit tests for one transformation"

clean:
	rm -rf runs/ .pytest_cache/ .coverage htmlcov/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
