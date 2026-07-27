.PHONY: install lint test dev clean

install:
	pip install --upgrade pip
	pip install uv
	uv sync --all-extras

lint:
	ruff check backend/src/
	ruff format --check backend/src/
	mypy backend/src/

lint-fix:
	ruff check --fix backend/src/
	ruff format backend/src/

test:
	pytest backend/tests/ -v --cov=backend/src

dev:
	docker compose up -d
	uv run uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache
	rm -rf backend/.venv
