"""A3/A4 del audit 2026-05-12: install_log_redactor enmascara secretos GRE/SOL."""

from __future__ import annotations

import logging

import pytest
from sunat_py.security.log_redactor import _SecretRedactor, install_log_redactor


@pytest.fixture
def isolated_logger():
    """Logger con namespace propio para no pisar otros tests."""
    name = "sunat_py._test_redactor"
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.filters.clear()
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.handlers.clear()
    logger.filters.clear()


def _capture(logger: logging.Logger) -> list[str]:
    captured: list[str] = []

    class _Sink(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(self.format(record))

    sink = _Sink()
    sink.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(sink)
    return captured


def test_install_redactor_masks_password(isolated_logger):
    install_log_redactor(loggers=(isolated_logger.name,))
    out = _capture(isolated_logger)
    isolated_logger.debug("body=grant_type=password&password=hunter2&client_id=X")
    assert "hunter2" not in out[0]
    assert "password=<redacted>" in out[0]


def test_install_redactor_masks_client_secret(isolated_logger):
    install_log_redactor(loggers=(isolated_logger.name,))
    out = _capture(isolated_logger)
    isolated_logger.debug("client_secret=mySecretValue123&scope=foo")
    assert "mySecretValue123" not in out[0]
    assert "client_secret=<redacted>" in out[0]


def test_install_redactor_masks_bearer(isolated_logger):
    install_log_redactor(loggers=(isolated_logger.name,))
    out = _capture(isolated_logger)
    isolated_logger.debug("headers: {'Authorization': 'Bearer abc.def.ghi'}")
    assert "abc.def.ghi" not in out[0]
    assert "Bearer <redacted>" in out[0]


def test_install_redactor_passthrough_when_no_secret(isolated_logger):
    install_log_redactor(loggers=(isolated_logger.name,))
    out = _capture(isolated_logger)
    isolated_logger.debug("conectando a api-cpe.sunat.gob.pe:443")
    assert out[0] == "conectando a api-cpe.sunat.gob.pe:443"


def test_install_redactor_idempotent(isolated_logger):
    install_log_redactor(loggers=(isolated_logger.name,))
    install_log_redactor(loggers=(isolated_logger.name,))
    install_log_redactor(loggers=(isolated_logger.name,))
    filters = [f for f in isolated_logger.filters if isinstance(f, _SecretRedactor)]
    assert len(filters) == 1


def test_install_redactor_with_args(isolated_logger):
    """getMessage() formatea el record con args; el filtro debe redactar el resultado."""
    install_log_redactor(loggers=(isolated_logger.name,))
    out = _capture(isolated_logger)
    isolated_logger.debug("envio %s", "password=hunter2")
    assert "hunter2" not in out[0]
    assert "password=<redacted>" in out[0]
