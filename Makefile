.PHONY: all setup run test clean

all: setup

setup:
	uv sync

run:
	uv run slurp $(ARGS)

test:
	uv run pytest

clean:
	rm -rf .pytest_cache dist build *.egg-info
	find . -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
