"""Pipeline end-to-end con mocks de SUNAT.

Verifica que la cadena builder -> packager -> mock SUNAT funcione sin
credenciales reales. No corre la firma porque eso requiere cert.
"""

from sunat_mock import (
    SAMPLE_CDR_ACCEPTED_XML,
    mock_get_status_accepted,
    mock_send_bill_accepted,
    mock_send_bill_rejected,
    mock_send_summary,
)
from sunat_py import build_invoice_xml, pack_invoice


def test_pipeline_build_pack_send_accepted(sample_invoice_input):
    """Build -> pack -> mock_send_bill devuelve aceptado."""
    xml = build_invoice_xml(sample_invoice_input)
    zip_bytes = pack_invoice(
        xml.encode("utf-8"),
        f"{sample_invoice_input.emisor.numero_doc}-01-F001-1",
    )

    result = mock_send_bill_accepted(zip_bytes, "F001-1.zip")

    assert result.status == "accepted"
    assert result.code == "0"
    assert "aceptada" in result.description
    assert result.cdr_xml == SAMPLE_CDR_ACCEPTED_XML


def test_pipeline_build_pack_send_rejected(sample_invoice_input):
    """Cuando SUNAT rechaza, el SDK devuelve status='rejected' con codigo y descripcion."""
    xml = build_invoice_xml(sample_invoice_input)
    zip_bytes = pack_invoice(
        xml.encode("utf-8"),
        f"{sample_invoice_input.emisor.numero_doc}-01-F001-1",
    )

    result = mock_send_bill_rejected(zip_bytes, "F001-1.zip", code="2017")

    assert result.status == "rejected"
    assert result.code == "2017"
    assert result.cdr_xml != b""


def test_pipeline_summary_ticket_then_status(sample_summary_input):
    """RC: send_summary devuelve ticket, get_status devuelve CDR."""
    from sunat_py import build_summary_xml

    xml = build_summary_xml(sample_summary_input)
    zip_bytes = pack_invoice(
        xml.encode("utf-8"),
        f"{sample_summary_input.emisor.numero_doc}-{sample_summary_input.id_rc}",
    )

    ticket = mock_send_summary(zip_bytes, "RC.zip")
    assert ticket
    assert ticket.isdigit()

    result = mock_get_status_accepted(ticket)
    assert result.status == "accepted"
    assert result.code == "0"
