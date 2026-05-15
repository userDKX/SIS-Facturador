"""Filtro de logging opt-in que enmascara secretos GRE/SOL.

El SDK no instala este filtro por su cuenta: el caller decide si quiere
modificar la cadena de loggers del proceso. Pensado para callers que
activan `logging.basicConfig(level=DEBUG)` para depurar trafico SUNAT y
no quieren que `password`, `client_secret` o el bearer token del GRE
aparezcan en cleartext en sus logs centralizados.

Uso:

    from sunat_py.security import install_log_redactor
    install_log_redactor()

Por defecto instala el filtro en los loggers `urllib3.connectionpool` y
`zeep`. Es idempotente: llamarla dos veces no agrega filtros duplicados.
"""

from __future__ import annotations

import logging
import re

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # form-encoded body de OAuth2 password grant
    (re.compile(r"(password=)([^&\s'\"]+)"), r"\1<redacted>"),
    (re.compile(r"(client_secret=)([^&\s'\"]+)"), r"\1<redacted>"),
    # bearer token en headers o en strings sueltos
    (re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)"), r"\1<redacted>"),
)


class _SecretRedactor(logging.Filter):
    """Reemplaza secretos en el mensaje del record antes de que se emita."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = message
        for pattern, replacement in _PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_log_redactor(*, loggers: tuple[str, ...] = ("urllib3.connectionpool", "zeep")) -> None:
    """Instala el filtro de redaccion en los loggers indicados.

    Idempotente: si el logger ya tiene un `_SecretRedactor`, no agrega
    uno nuevo. No toca otros filtros ni handlers que el caller tenga.
    """
    redactor = _SecretRedactor()
    for name in loggers:
        target = logging.getLogger(name)
        if any(isinstance(f, _SecretRedactor) for f in target.filters):
            continue
        target.addFilter(redactor)
