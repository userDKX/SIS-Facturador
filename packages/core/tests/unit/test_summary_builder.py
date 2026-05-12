from datetime import date
from decimal import Decimal

import pytest
from lxml import etree
from sunat_py import (
    Party,
    SummaryDocumentsInput,
    SummaryItem,
    ValidationError,
    build_summary_xml,
    today_lima,
)

NS_RC = "urn:sunat:names:specification:ubl:peru:schema:xsd:SummaryDocuments-1"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_SAC = "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1"


def test_id_rc_se_construye_con_fecha_referencia_y_correlativo():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    rc = SummaryDocumentsInput(
        correlativo=3,
        fecha_referencia=date(2026, 5, 8),
        fecha_emision=date(2026, 5, 9),
        emisor=emisor,
        items=[
            SummaryItem(
                tipo_doc="03",
                serie="B001",
                numero=1,
                cliente_tipo_doc="1",
                cliente_numero_doc="12345678",
                moneda="PEN",
                total=Decimal("100"),
                base_gravada=Decimal("84.75"),
                igv=Decimal("15.25"),
            )
        ],
    )
    assert rc.id_rc == "RC-20260508-3"


def test_build_summary_xml_root(sample_summary_input):
    xml = build_summary_xml(sample_summary_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_RC}}}SummaryDocuments"


def test_build_summary_xml_id_y_fechas(sample_summary_input):
    xml = build_summary_xml(sample_summary_input)
    root = etree.fromstring(xml.encode("utf-8"))

    fecha_ref = sample_summary_input.fecha_referencia.strftime("%Y%m%d")
    assert root.find(f"{{{NS_CBC}}}ID").text == f"RC-{fecha_ref}-1"
    assert (
        root.find(f"{{{NS_CBC}}}ReferenceDate").text
        == sample_summary_input.fecha_referencia.isoformat()
    )


def test_build_summary_xml_linea_boleta(sample_summary_input):
    xml = build_summary_xml(sample_summary_input)
    root = etree.fromstring(xml.encode("utf-8"))

    line = root.find(f"{{{NS_SAC}}}SummaryDocumentsLine")
    assert line is not None

    assert line.find(f"{{{NS_CBC}}}DocumentTypeCode").text == "03"
    assert line.find(f"{{{NS_CBC}}}ID").text == "B001-1"

    cliente_id = line.find(
        f"{{{NS_CAC}}}AccountingCustomerParty/{{{NS_CBC}}}CustomerAssignedAccountID"
    )
    cliente_tipo = line.find(f"{{{NS_CAC}}}AccountingCustomerParty/{{{NS_CBC}}}AdditionalAccountID")
    assert cliente_id.text == "12345678"
    assert cliente_tipo.text == "1"

    estado = line.find(f"{{{NS_CAC}}}Status/{{{NS_CBC}}}ConditionCode")
    assert estado.text == "1"

    total = line.find(f"{{{NS_SAC}}}TotalAmount")
    assert total.get("currencyID") == "PEN"
    assert Decimal(total.text) == Decimal("118.00")

    igv = line.find(f"{{{NS_CAC}}}TaxTotal/{{{NS_CBC}}}TaxAmount")
    assert Decimal(igv.text) == Decimal("18.00")


def test_build_summary_xml_tipo_doc_factura_falla():
    """Las facturas no van en RC, va via sendBill directo."""
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    rc = SummaryDocumentsInput(
        correlativo=1,
        fecha_referencia=today_lima(),
        fecha_emision=today_lima(),
        emisor=emisor,
        items=[
            SummaryItem(
                tipo_doc="01",
                serie="F001",
                numero=1,
                cliente_tipo_doc="6",
                cliente_numero_doc="20100070970",
                moneda="PEN",
                total=Decimal("100"),
                base_gravada=Decimal("84.75"),
                igv=Decimal("15.25"),
            )
        ],
    )
    with pytest.raises(ValidationError, match="tipo_doc"):
        build_summary_xml(rc)


def test_build_summary_xml_estado_invalido_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    rc = SummaryDocumentsInput(
        correlativo=1,
        fecha_referencia=today_lima(),
        fecha_emision=today_lima(),
        emisor=emisor,
        items=[
            SummaryItem(
                tipo_doc="03",
                serie="B001",
                numero=1,
                cliente_tipo_doc="1",
                cliente_numero_doc="12345678",
                moneda="PEN",
                total=Decimal("100"),
                base_gravada=Decimal("84.75"),
                igv=Decimal("15.25"),
                estado="9",
            )
        ],
    )
    with pytest.raises(ValidationError, match="estado"):
        build_summary_xml(rc)


def test_build_summary_xml_extension_content_vacio(sample_summary_input):
    xml = build_summary_xml(sample_summary_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ext = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext is not None and len(ext) == 0
