.PHONY: setup \
        deploy-simplismart deploy-simplismart-only \
        deploy-fireworks deploy-all \
        teardown-simplismart teardown-fireworks teardown-all \
        dry-run benchmark-p0 benchmark-all report test clean

setup:
	python3 -m venv .venv && \
	.venv/bin/pip install --upgrade pip && \
	.venv/bin/pip install --pre -r requirements.txt

# Full flow: compile from HuggingFace then deploy (skips compile if SIMPLISMART_MODEL_REPO_UUID set)
deploy-simplismart:
	.venv/bin/python deploy/deploy_simplismart.py

# Deploy only (skip compile) — requires SIMPLISMART_MODEL_REPO_UUID in .env
deploy-simplismart-only:
	.venv/bin/python deploy/deploy_simplismart.py --deploy-only

deploy-fireworks:
	.venv/bin/python deploy/deploy_fireworks.py

# Sequential: Simplismart first, then Fireworks
deploy-all:
	.venv/bin/python deploy/deploy_simplismart.py && .venv/bin/python deploy/deploy_fireworks.py

teardown-simplismart:
	.venv/bin/python deploy/teardown_simplismart.py

teardown-fireworks:
	.venv/bin/python deploy/teardown_fireworks.py

teardown-all:
	.venv/bin/python deploy/teardown_simplismart.py; .venv/bin/python deploy/teardown_fireworks.py

dry-run:
	.venv/bin/python -m benchmark.runner --dry-run

benchmark-p0:
	.venv/bin/python -m benchmark.runner --platform both --priority p0

benchmark-all:
	.venv/bin/python -m benchmark.runner --platform both --priority all

report:
	.venv/bin/python -m benchmark.report

test:
	.venv/bin/pytest tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f data/results/*_raw.csv
