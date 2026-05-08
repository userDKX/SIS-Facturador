.PHONY: help install install-dev lint fmt test test-beta cov run verify-cert sendbill-beta sendbill-prod sendbill-prod-boleta clean precommit-install precommit-run

# Default target
help:
	@echo "SIS Facturador (workspace) - targets disponibles"
	@echo ""
	@echo "Setup"
	@echo "  install            Instala packages/core + packages/api en modo editable"
	@echo "  install-dev        install + dev tools (ruff, mypy, pytest-cov, pre-commit)"
	@echo "  precommit-install  Activa pre-commit hooks en este clon"
	@echo ""
	@echo "Calidad"
	@echo "  lint               ruff check sobre todo el repo"
	@echo "  fmt                ruff format + autofix"
	@echo "  precommit-run      Corre todos los hooks contra todo el repo"
	@echo ""
	@echo "Tests"
	@echo "  test               unit + e2e (skipea beta SUNAT)"
	@echo "  test-beta          Integracion contra SUNAT beta (necesita envs MODDATOS)"
	@echo "  cov                Coverage HTML + terminal"
	@echo ""
	@echo "Run"
	@echo "  run                uvicorn dev server con reload (microservicio)"
	@echo "  verify-cert        Validacion local del cert (sin tocar SUNAT)"
	@echo "  sendbill-beta      Homologacion: manda Factura a SUNAT beta"
	@echo "  sendbill-prod      PRODUCCION: emite Factura real (--confirm-real)"
	@echo "  sendbill-prod-boleta PRODUCCION: emite Boleta real (--confirm-real)"
	@echo ""
	@echo "Misc"
	@echo "  clean              Limpia caches, coverage, build artifacts"

install:
	pip install -e packages/core
	pip install -e packages/api

install-dev:
	pip install -r requirements-dev.txt

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
	pytest --cov-report=term --cov-report=html
	@echo "HTML report: htmlcov/index.html"

run:
	uvicorn sis_facturador.main:app --reload

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
	@python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('*.egg-info')]"
	@echo "Limpio: caches y build artifacts."
