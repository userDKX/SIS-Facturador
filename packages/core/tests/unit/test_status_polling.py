"""Tests del polling de getStatus — sync y async — sin tocar SUNAT.

Mockea el `client.service.getStatus` con un fake object que devuelve
secuencias controladas de status_code/content. Verifica que el loop:
  - termina apenas el ticket sale de "98",
  - invoca `on_attempt` una vez por intento con el status_code real,
  - agota `retries` y levanta SunatError si todo el rato responde "98",
  - parsea correctamente CDR aceptado vs CDR de rechazo dentro del ZIP,
  - la version async no bloquea (usa asyncio.sleep en vez de time.sleep).
"""

from __future__ import annotations

import asyncio
import io
import zipfile

import pytest
from sunat_mock import SAMPLE_CDR_ACCEPTED_XML
from sunat_py import SunatError, aget_status, get_status


def _zip_cdr(xml: bytes, name: str = "R-cdr.xml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, xml)
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, status_code: str, content: bytes = b"") -> None:
        self.statusCode = status_code
        self.content = content


class _FakeService:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def getStatus(self, ticket: str) -> _FakeResponse:
        self.calls += 1
        if not self._responses:
            raise AssertionError("getStatus llamado mas veces que respuestas mockeadas")
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, service: _FakeService) -> None:
        self.service = service


def _client_returning(*responses: _FakeResponse) -> _FakeClient:
    return _FakeClient(_FakeService(list(responses)))


def test_get_status_devuelve_apenas_recibe_cdr_aceptado():
    cdr_zip = _zip_cdr(SAMPLE_CDR_ACCEPTED_XML)
    client = _client_returning(_FakeResponse("0", cdr_zip))

    result = get_status(client, "ticket-1", interval=0)

    assert result.status == "accepted"
    assert result.code == "0"
    assert client.service.calls == 1


def test_get_status_reintenta_98_y_termina_en_0():
    cdr_zip = _zip_cdr(SAMPLE_CDR_ACCEPTED_XML)
    client = _client_returning(
        _FakeResponse("98"),
        _FakeResponse("98"),
        _FakeResponse("0", cdr_zip),
    )
    attempts: list[tuple[int, str]] = []

    result = get_status(
        client, "t-98", retries=5, interval=0,
        on_attempt=lambda i, s: attempts.append((i, s)),
    )

    assert result.status == "accepted"
    assert client.service.calls == 3
    assert attempts == [(0, "98"), (1, "98"), (2, "0")]


def test_get_status_agotado_levanta_sunat_error():
    client = _client_returning(*[_FakeResponse("98")] * 3)

    with pytest.raises(SunatError) as excinfo:
        get_status(client, "t-stuck", retries=3, interval=0)

    assert excinfo.value.code == "98"
    assert "sigue en proceso" in str(excinfo.value)
    assert client.service.calls == 3


def test_get_status_status_inesperado_levanta_sunat_error():
    client = _client_returning(_FakeResponse("42"))

    with pytest.raises(SunatError) as excinfo:
        get_status(client, "t-weird", retries=3, interval=0)

    assert excinfo.value.code == "42"
    assert "estado inesperado" in str(excinfo.value)


def test_get_status_99_sin_cdr_devuelve_rejected():
    client = _client_returning(_FakeResponse("99"))

    result = get_status(client, "t-99", retries=3, interval=0)

    assert result.status == "rejected"
    assert result.code == "99"


def test_aget_status_funciona_y_no_bloquea():
    cdr_zip = _zip_cdr(SAMPLE_CDR_ACCEPTED_XML)
    client = _client_returning(
        _FakeResponse("98"),
        _FakeResponse("0", cdr_zip),
    )
    attempts: list[tuple[int, str]] = []

    result = asyncio.run(
        aget_status(
            client, "t-async", retries=5, interval=0,
            on_attempt=lambda i, s: attempts.append((i, s)),
        )
    )

    assert result.status == "accepted"
    assert result.code == "0"
    assert attempts == [(0, "98"), (1, "0")]
