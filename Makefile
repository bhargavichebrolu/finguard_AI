# Developer shortcuts. Each recipe is one documented command, so anyone without make
# (the default on Windows) can copy it into a terminal unchanged.

UV_RUN = uv run --project backend

.PHONY: setup data validate prepare eda audit drift train select explain diagnose final-test export env db-up stack migrate serve admin test test-fast test-phase3 lint docs-check frontend-build

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

drift:
	$(UV_RUN) python scripts/analyse_temporal_drift.py

train:
	$(UV_RUN) python scripts/train_models.py

select:
	$(UV_RUN) python scripts/evaluate_models.py

explain:
	$(UV_RUN) python scripts/explain_model.py

diagnose:
	$(UV_RUN) python scripts/diagnose_lightgbm.py

final-test:
	$(UV_RUN) python scripts/evaluate_final_test.py

export:
	$(UV_RUN) python scripts/export_metrics.py

env:
	$(UV_RUN) python scripts/generate_env.py --api-port 8010

db-up:
	docker compose up -d --wait db

stack:
	docker compose up -d --build --wait

migrate:
	cd backend && uv run alembic upgrade head

serve:
	cd backend && uv run uvicorn app.main:app --port 8010

admin:
	$(UV_RUN) python scripts/create_admin.py --email $(EMAIL)

test:
	$(UV_RUN) pytest backend/tests --rootdir backend -c backend/pyproject.toml

test-phase3:
	$(UV_RUN) pytest backend/tests --rootdir backend -c backend/pyproject.toml --deselect tests/integration/test_real_models.py::test_test_results_can_be_recalculated_from_the_saved_model

test-fast:
	$(UV_RUN) pytest backend/tests --rootdir backend -c backend/pyproject.toml -m "not real_data and not database"

lint:
	$(UV_RUN) ruff check backend scripts --config backend/pyproject.toml

docs-check:
	$(UV_RUN) python scripts/check_explanations.py

frontend-build:
	cd frontend && npm run build
