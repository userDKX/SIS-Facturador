"""Cliente SOAP para el WS de SUNAT (SEE-DSC).

El SDK no cachea el cliente zeep ni decide donde vienen las credenciales.
El caller construye un Client una vez con `build_zeep_client(...)` y lo
reutiliza llamando `send_bill(client, ...)`. Eso permite el caso
single-tenant (un cache global) y el multi-tenant (un client por tenant).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lxml import etree
from zeep import Client
from zeep import Settings as ZeepSettings
from zeep.exceptions import Fault as ZeepFault
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken

from sunat_py.sunat.packager import unpack_cdr

WSDL_DIR = Path(__file__).resolve().parent / "wsdl"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

SunatMode = Literal["beta", "prod"]
SunatStatus = Literal["accepted", "accepted_with_obs", "rejected"]


@dataclass(frozen=True)
class SunatResult:
    status: SunatStatus
    code: str
    description: str
    cdr_xml: bytes


class SunatError(Exception):
    """Error de SUNAT que NO es un rechazo de negocio (transport, fault no parseable, etc)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"SUNAT error {code}: {message}")


def build_zeep_client(
    mode: SunatMode,
    ruc: str,
    username: str,
    password: str,
    timeout: int = 120,
) -> Client:
    """Construye un cliente zeep contra el WSDL local de SUNAT.

    `username` es el user del secundario sin el RUC. Internamente se
    concatena `{ruc}{username}` para WS-Security UsernameToken.

    Usa WSDLs bundleados localmente en `wsdl/{beta,prod}/` porque SUNAT
    rate-limita el endpoint del import `?ns1.wsdl`: la primera fetch
    responde 200, las siguientes 401, y zeep hace varias durante init.
    """
    wsdl_path = WSDL_DIR / mode / "billService.wsdl"
    if not wsdl_path.exists():
        raise RuntimeError(f"WSDL local no encontrado: {wsdl_path}")

    wsse = UsernameToken(f"{ruc}{username}", password)
    transport = Transport(timeout=timeout, operation_timeout=timeout)
    # strict=True valida la respuesta contra el WSDL; sin xml_huge_tree
    # cerramos la puerta a Billion Laughs / entity bombs en el CDR.
    zeep_settings = ZeepSettings(strict=True)
    return Client(
        wsdl=str(wsdl_path),
        wsse=wsse,
        transport=transport,
        settings=zeep_settings,
    )


def _parse_cdr(cdr_xml: bytes) -> tuple[str, str]:
    """Devuelve (response_code, description) del CDR XML de SUNAT."""
    root = etree.fromstring(cdr_xml)
    code_el = root.find(f".//{{{NS_CBC}}}ResponseCode")
    desc_el = root.find(f".//{{{NS_CBC}}}Description")
    code = code_el.text if code_el is not None and code_el.text else ""
    description = desc_el.text if desc_el is not None and desc_el.text else ""
    return code, description


def _classify(code: str) -> SunatStatus:
    if code == "0":
        return "accepted"
    if code == "098":
        return "accepted_with_obs"
    return "rejected"


def _extract_fault_code(fault: ZeepFault) -> str:
    """Extrae el codigo numerico de un SOAP Fault de SUNAT.

    SUNAT envia faults con codigo tipo `soap-env:Client.0306` donde 0306
    es el codigo SUNAT del error. Devuelve el sufijo numerico si existe.
    """
    raw = str(fault.code) if fault.code else ""
    if "." in raw:
        return raw.rsplit(".", 1)[-1]
    return raw


def send_summary(client: Client, zip_bytes: bytes, filename: str) -> str:
    """Envia un RC, RA o SR a SUNAT via sendSummary (asincrono).

    Devuelve el ticket numerico. SUNAT procesa el resumen y publica el CDR
    minutos despues. Para obtener el CDR, llamar a `get_status(client, ticket)`
    (que hace polling) cuando se necesite.
    """
    try:
        ticket = client.service.sendSummary(fileName=filename, contentFile=zip_bytes)
    except ZeepFault as fault:
        code = _extract_fault_code(fault)
        message = str(fault.message) if fault.message else str(fault)
        raise SunatError(code=code or "fault", message=message) from fault
    except Exception as exc:
        raise SunatError(code="transport", message=str(exc)) from exc
    if not ticket:
        raise SunatError(code="empty", message="SUNAT no devolvio ticket")
    return str(ticket)


def _check_status_once(
    client: Client, ticket: str
) -> tuple[Literal["done", "in_progress"], str, SunatResult | None]:
    """Una sola llamada a `getStatus(ticket)`.

    Devuelve la tupla `(estado_interno, status_code_sunat, resultado)`:
      * ("done", code, SunatResult) cuando hay CDR (aceptado u observado u 99).
      * ("in_progress", "98", None) cuando SUNAT aun procesa.
    Para cualquier otro statusCode levanta SunatError. El caller decide si
    sigue esperando o no.
    """
    try:
        response = client.service.getStatus(ticket=ticket)
    except ZeepFault as fault:
        code = _extract_fault_code(fault)
        message = str(fault.message) if fault.message else str(fault)
        raise SunatError(code=code or "fault", message=message) from fault
    except Exception as exc:
        raise SunatError(code="transport", message=str(exc)) from exc

    status_code = str(getattr(response, "statusCode", "") or "")
    content = getattr(response, "content", b"") or b""

    if status_code == "0" and content:
        cdr_xml = unpack_cdr(content)
        code, description = _parse_cdr(cdr_xml)
        return (
            "done",
            status_code,
            SunatResult(
                status=_classify(code),
                code=code,
                description=description,
                cdr_xml=cdr_xml,
            ),
        )

    if status_code == "99":
        if content:
            try:
                cdr_xml = unpack_cdr(content)
                code, description = _parse_cdr(cdr_xml)
                return (
                    "done",
                    status_code,
                    SunatResult(
                        status="rejected",
                        code=code,
                        description=description,
                        cdr_xml=cdr_xml,
                    ),
                )
            except Exception:
                pass
        return (
            "done",
            status_code,
            SunatResult(
                status="rejected",
                code="99",
                description="ticket procesado con errores",
                cdr_xml=b"",
            ),
        )

    if status_code == "98":
        return "in_progress", status_code, None

    raise SunatError(
        code=status_code or "unknown",
        message=f"estado inesperado para ticket {ticket}: {status_code!r}",
    )


def get_status(
    client: Client,
    ticket: str,
    *,
    retries: int = 10,
    interval: float = 3.0,
    on_attempt: Callable[[int, str], None] | None = None,
) -> SunatResult:
    """Consulta el estado de un envio asincrono (RC/RA/SR) con polling.

    SUNAT puede tardar segundos a minutos en procesar un resumen. Esta
    funcion consulta `getStatus(ticket)` hasta `retries` veces con
    `interval` segundos entre intentos, o hasta recibir un estado terminal.

    Estados de SUNAT:
      * "0"  -> procesado correctamente, devuelve CDR de aceptacion.
      * "98" -> en proceso, reintentar.
      * "99" -> procesado con errores, el CDR (si existe) trae el detalle.
      * otros -> error tecnico no esperado.

    `on_attempt(attempt_index, status_code)` se invoca despues de cada
    consulta antes de dormir — util para loggear "ticket X intento N: 98"
    o exponer el progreso a otra capa sin tener que envolver la funcion.
    """
    for attempt in range(retries):
        outcome, status_code, result = _check_status_once(client, ticket)
        if on_attempt is not None:
            on_attempt(attempt, status_code)
        if outcome == "done":
            assert result is not None
            return result
        if attempt + 1 < retries:
            time.sleep(interval)

    raise SunatError(
        code="98",
        message=f"ticket {ticket}: sigue en proceso tras {retries} intentos",
    )


async def aget_status(
    client: Client,
    ticket: str,
    *,
    retries: int = 10,
    interval: float = 3.0,
    on_attempt: Callable[[int, str], None] | None = None,
) -> SunatResult:
    """Version async de `get_status` — no bloquea el event loop al esperar.

    Misma logica de polling que la version sync, pero la llamada SOAP se
    despacha a un thread (zeep no es async-native) y la espera entre
    intentos usa `asyncio.sleep`. Pensado para servidores async (FastAPI,
    starlette) donde bloquear el loop con `time.sleep` corta latencia
    de otras requests durante minutos.
    """
    for attempt in range(retries):
        outcome, status_code, result = await asyncio.to_thread(_check_status_once, client, ticket)
        if on_attempt is not None:
            on_attempt(attempt, status_code)
        if outcome == "done":
            assert result is not None
            return result
        if attempt + 1 < retries:
            await asyncio.sleep(interval)

    raise SunatError(
        code="98",
        message=f"ticket {ticket}: sigue en proceso tras {retries} intentos",
    )


def send_bill(client: Client, zip_bytes: bytes, filename: str) -> SunatResult:
    """Envia un comprobante a SUNAT via sendBill (sincrono).

    Para faults numericos (rechazos de negocio) devuelve SunatResult con
    `status='rejected'`. Para faults no numericos o errores de transporte
    levanta SunatError.
    """
    try:
        response_b64 = client.service.sendBill(fileName=filename, contentFile=zip_bytes)
    except ZeepFault as fault:
        code = _extract_fault_code(fault)
        description = str(fault.message) if fault.message else str(fault)
        if code.isdigit():
            return SunatResult(
                status="rejected",
                code=code,
                description=description,
                cdr_xml=b"",
            )
        raise SunatError(code=code or "fault", message=description) from fault
    except Exception as exc:
        raise SunatError(code="transport", message=str(exc)) from exc

    if not response_b64:
        raise SunatError(code="empty", message="SUNAT devolvio una respuesta vacia")

    cdr_xml = unpack_cdr(response_b64)
    code, description = _parse_cdr(cdr_xml)
    return SunatResult(
        status=_classify(code),
        code=code,
        description=description,
        cdr_xml=cdr_xml,
    )
