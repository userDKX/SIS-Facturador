.PHONY: help install install-dev lint fmt test test-beta cov run verify-cert sendbill-beta sendbill-prod sendbill-prod-boleta clean precommit-install precommit-run

# Default target shown when running `make` with no args
help:
	@echo "SIS Facturador - available targets"
	@echo ""
	@echo "Setup"
	@echo "  install            Install runtime deps only"
	@echo "  install-dev        Install runtime + dev deps (ruff/mypy/pytest-cov/pre-commit)"
	@echo "  precommit-install  Activate pre-commit hooks in this repo"
	@echo ""
	@echo "Quality"
	@echo "  lint               Ruff lint check"
	@echo "  fmt                Ruff format + autofix"
	@echo "  precommit-run      Run all pre-commit hooks against the whole repo"
	@echo ""
	@echo "Tests"
	@echo "  test               Unit + integration (skip beta SUNAT)"
	@echo "  test-beta          Integration against SUNAT beta (needs MODDATOS envs)"
	@echo "  cov                Coverage report (HTML + terminal)"
	@echo ""
	@echo "Run"
	@echo "  run                uvicorn dev server with reload"
	@echo "  verify-cert        Local cert validation (no SUNAT contact)"
	@echo "  sendbill-beta      Homologation: send a Factura to SUNAT beta"
	@echo "  sendbill-prod      PRODUCTION: send a real Factura (--confirm-real)"
	@echo "  sendbill-prod-boleta PRODUCTION: send a real Boleta (--confirm-real)"
	@echo ""
	@echo "Misc"
	@echo "  clean              Remove caches, coverage and build artifacts"

install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"

precommit-install:
	pre-commit install

precommit-run:
	pre-commit run --all-files

lint:
	ruff check .

fmt:
	ruff format .
	ruff check --fix .

test:
	pytest -m "not beta"

test-beta:
	pytest -m beta

cov:
	pytest --cov=app --cov-report=term --cov-report=html
	@echo "HTML report: htmlcov/index.html"

run:
	uvicorn app.main:app --reload

verify-cert:
	python scripts/verify_cert.py

sendbill-beta:
	python scripts/sendbill_beta.py

sendbill-prod:
	python scripts/sendbill_prod.py --confirm-real

sendbill-prod-boleta:
	python scripts/sendbill_prod_boleta.py --confirm-real

clean:
	@python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	@python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['htmlcov', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.coverage', 'build', 'dist']]"
	@echo "Cleaned caches and build artifacts."
