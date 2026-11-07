# Developer shortcuts. Each recipe is one documented command, so anyone without make
# (the default on Windows) can copy it into a terminal unchanged.

UV_RUN = uv run --project backend

.PHONY: setup data validate prepare eda audit drift train select explain final-test export test test-fast lint docs-check frontend-build

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

final-test:
	$(UV_RUN) python scripts/evaluate_final_test.py

export:
	$(UV_RUN) python scripts/export_metrics.py

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
