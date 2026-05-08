"""Cliente SOAP para el WS de SUNAT (SEE-DSC).

El SDK no cachea el cliente zeep ni decide donde vienen las credenciales.
El caller construye un Client una vez con `build_zeep_client(...)` y lo
reutiliza llamando `send_bill(client, ...)`. Eso permite el caso
single-tenant (un cache global) y el multi-tenant (un client por tenant).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lxml import etree
from zeep import Client
from zeep import Settings as ZeepSettings
from zeep.exceptions import Fault as ZeepFault
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken

from pe_invoicing.sunat.packager import unpack_cdr

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
    zeep_settings = ZeepSettings(strict=False, xml_huge_tree=True)
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
