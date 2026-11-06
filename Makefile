# Developer shortcuts. Each recipe is one documented command, so anyone without make
# (the default on Windows) can copy it into a terminal unchanged.

UV_RUN = uv run --project backend

.PHONY: setup data validate prepare eda audit test test-fast lint docs-check frontend-build

setup:
	uv sync --project backend
	cd frontend && npm ci

data: validate prepare eda audit

validate:
	$(UV_RUN) python scripts/validate_dataset.py

prepare:
	$(UV_RUN) python scripts/prepare_dataset.py

eda:
	$(UV_RUN) python scripts/run_eda.py

audit:
	$(UV_RUN) python scripts/audit_leakage.py

test:
	$(UV_RUN) pytest backend/tests --rootdir backend -c backend/pyproject.toml

test-fast:
	$(UV_RUN) pytest backend/tests --rootdir backend -c backend/pyproject.toml -m "not real_data"

lint:
	$(UV_RUN) ruff check backend scripts --config backend/pyproject.toml

docs-check:
	$(UV_RUN) python scripts/check_explanations.py

frontend-build:
	cd frontend && npm run build
