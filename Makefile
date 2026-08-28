.PHONY: install test run-api run-ui pipeline init-sample

install:
	cd platform && pip install -e ".[dev]"

test:
	cd platform && pytest -v

run-api:
	cd platform && uvicorn migrate_framework.api.main:app --reload --port 8080

run-ui:
	cd platform && streamlit run migrate_framework/ui/app.py

init-sample:
	cd platform && migrate-framework init \
		--name "EuroSA Bank" \
		--source ../sample-bank \
		--landscape ../sample-bank/landscape-manifest.yaml

pipeline:
	powershell -ExecutionPolicy Bypass -File scripts/run_pipeline.ps1
