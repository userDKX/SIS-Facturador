from datetime import date

import pytest
from lxml import etree
from sunat_py import (
    Party,
    ValidationError,
    VoidedDocumentsInput,
    VoidedItem,
    build_voided_xml,
    today_lima,
)

NS_RA = "urn:sunat:names:specification:ubl:peru:schema:xsd:VoidedDocuments-1"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_SAC = "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1"


def test_id_ra_se_construye_con_fecha_referencia_y_correlativo():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    ra = VoidedDocumentsInput(
        correlativo=7,
        fecha_referencia=date(2026, 5, 8),
        fecha_emision=date(2026, 5, 11),
        emisor=emisor,
        items=[VoidedItem(tipo_doc="01", serie="F001", numero=1, motivo="x")],
    )
    assert ra.id_ra == "RA-20260508-7"


def test_build_voided_xml_root(sample_voided_input):
    xml = build_voided_xml(sample_voided_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_RA}}}VoidedDocuments"


def test_build_voided_xml_id_y_fechas(sample_voided_input):
    xml = build_voided_xml(sample_voided_input)
    root = etree.fromstring(xml.encode("utf-8"))

    fecha_ref = sample_voided_input.fecha_referencia.strftime("%Y%m%d")
    assert root.find(f"{{{NS_CBC}}}ID").text == f"RA-{fecha_ref}-1"
    assert (
        root.find(f"{{{NS_CBC}}}ReferenceDate").text
        == sample_voided_input.fecha_referencia.isoformat()
    )
    assert (
        root.find(f"{{{NS_CBC}}}IssueDate").text
        == sample_voided_input.fecha_emision.isoformat()
    )


def test_build_voided_xml_tiene_voided_line(sample_voided_input):
    xml = build_voided_xml(sample_voided_input)
    root = etree.fromstring(xml.encode("utf-8"))

    line = root.find(f"{{{NS_SAC}}}VoidedDocumentsLine")
    assert line is not None

    assert line.find(f"{{{NS_CBC}}}DocumentTypeCode").text == "01"
    assert line.find(f"{{{NS_SAC}}}DocumentSerialID").text == "F001"
    assert line.find(f"{{{NS_SAC}}}DocumentNumberID").text == "1"
    assert line.find(f"{{{NS_SAC}}}VoidReasonDescription").text == "ERROR EN DATOS"


def test_build_voided_xml_extension_content_vacio(sample_voided_input):
    xml = build_voided_xml(sample_voided_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ext = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext is not None and len(ext) == 0


def test_build_voided_xml_items_vacios_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    ra = VoidedDocumentsInput(
        correlativo=1,
        fecha_referencia=today_lima(),
        fecha_emision=today_lima(),
        emisor=emisor,
        items=[],
    )
    with pytest.raises(ValidationError, match="items"):
        build_voided_xml(ra)


def test_build_voided_xml_tipo_doc_invalido_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    ra = VoidedDocumentsInput(
        correlativo=1,
        fecha_referencia=today_lima(),
        fecha_emision=today_lima(),
        emisor=emisor,
        items=[
            VoidedItem(tipo_doc="09", serie="T001", numero=1, motivo="GRE no se anula con RA"),
        ],
    )
    with pytest.raises(ValidationError, match="tipo_doc"):
        build_voided_xml(ra)


def test_build_voided_xml_motivo_vacio_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    ra = VoidedDocumentsInput(
        correlativo=1,
        fecha_referencia=today_lima(),
        fecha_emision=today_lima(),
        emisor=emisor,
        items=[VoidedItem(tipo_doc="01", serie="F001", numero=1, motivo="")],
    )
    with pytest.raises(ValidationError, match="motivo"):
        build_voided_xml(ra)
