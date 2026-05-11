"""Mocks de SUNAT que reproducen el contrato del cliente SOAP.

No usan zeep ni hablan con la red. Devuelven `SunatResult` directamente
(o el `str` del ticket en el caso de `sendSummary`). Los CDR de ejemplo
imitan la forma real de SUNAT: ApplicationResponse UBL con ResponseCode
y Description, suficiente para que `_parse_cdr` extraiga lo necesario.
"""

from sunat_py.sunat.client import SunatResult

SAMPLE_CDR_ACCEPTED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<ar:ApplicationResponse
    xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.0</cbc:UBLVersionID>
  <cbc:CustomizationID>1.0</cbc:CustomizationID>
  <cbc:ID>1</cbc:ID>
  <cbc:IssueDate>2026-05-08</cbc:IssueDate>
  <cbc:ResponseDate>2026-05-08</cbc:ResponseDate>
  <cbc:ResponseTime>12:00:00</cbc:ResponseTime>
  <cac:DocumentResponse>
    <cac:Response>
      <cbc:ReferenceID>F001-1</cbc:ReferenceID>
      <cbc:ResponseCode>0</cbc:ResponseCode>
      <cbc:Description>La Factura numero F001-1, ha sido aceptada</cbc:Description>
    </cac:Response>
  </cac:DocumentResponse>
</ar:ApplicationResponse>
"""

SAMPLE_CDR_REJECTED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<ar:ApplicationResponse
    xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.0</cbc:UBLVersionID>
  <cbc:CustomizationID>1.0</cbc:CustomizationID>
  <cbc:ID>1</cbc:ID>
  <cbc:IssueDate>2026-05-08</cbc:IssueDate>
  <cbc:ResponseDate>2026-05-08</cbc:ResponseDate>
  <cac:DocumentResponse>
    <cac:Response>
      <cbc:ReferenceID>F001-1</cbc:ReferenceID>
      <cbc:ResponseCode>2329</cbc:ResponseCode>
      <cbc:Description>La fecha de emision esta fuera del periodo de declaracion</cbc:Description>
    </cac:Response>
  </cac:DocumentResponse>
</ar:ApplicationResponse>
"""


def mock_send_bill_accepted(zip_bytes: bytes = b"", filename: str = "") -> SunatResult:
    """Imita `send_bill` cuando SUNAT acepta el comprobante (code 0)."""
    return SunatResult(
        status="accepted",
        code="0",
        description="La Factura numero F001-1, ha sido aceptada",
        cdr_xml=SAMPLE_CDR_ACCEPTED_XML,
    )


def mock_send_bill_rejected(
    zip_bytes: bytes = b"",
    filename: str = "",
    *,
    code: str = "2329",
    description: str = "La fecha de emision esta fuera del periodo de declaracion",
) -> SunatResult:
    """Imita `send_bill` cuando SUNAT rechaza por validacion de negocio."""
    return SunatResult(
        status="rejected",
        code=code,
        description=description,
        cdr_xml=SAMPLE_CDR_REJECTED_XML,
    )


def mock_send_summary(zip_bytes: bytes = b"", filename: str = "") -> str:
    """Imita `send_summary` devolviendo un ticket dummy."""
    return "1234567890123456"


def mock_get_status_accepted(ticket: str = "") -> SunatResult:
    """Imita `get_status` cuando el resumen fue procesado correctamente."""
    return SunatResult(
        status="accepted",
        code="0",
        description="El resumen fue procesado correctamente",
        cdr_xml=SAMPLE_CDR_ACCEPTED_XML,
    )


def mock_get_status_in_progress_then_accepted():
    """Generador que simula polling: primero "en proceso", luego "aceptado"."""
    attempts = [
        SunatResult(status="rejected", code="98", description="En proceso", cdr_xml=b""),
        SunatResult(
            status="accepted",
            code="0",
            description="El resumen fue procesado correctamente",
            cdr_xml=SAMPLE_CDR_ACCEPTED_XML,
        ),
    ]
    yield from attempts
