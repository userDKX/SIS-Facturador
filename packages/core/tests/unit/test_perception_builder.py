from datetime import date
from decimal import Decimal

import pytest
from lxml import etree
from sunat_py import Party, ValidationError, today_lima
from sunat_py.ubl.builder import build_perception_xml
from sunat_py.ubl.models import PerceptionDocReference, PerceptionInput

NS_PER = "urn:sunat:names:specification:ubl:peru:schema:xsd:Perception-1"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_SAC = "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1"


def test_build_perception_xml_root(sample_perception_input):
    xml = build_perception_xml(sample_perception_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_PER}}}Perception"


def test_build_perception_xml_ubl_version_y_customization(sample_perception_input):
    xml = build_perception_xml(sample_perception_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.find(f"{{{NS_CBC}}}UBLVersionID").text == "2.0"
    assert root.find(f"{{{NS_CBC}}}CustomizationID").text == "1.0"


def test_build_perception_xml_id_y_fecha(sample_perception_input):
    xml = build_perception_xml(sample_perception_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.find(f"{{{NS_CBC}}}ID").text == "P001-1"
    assert (
        root.find(f"{{{NS_CBC}}}IssueDate").text
        == sample_perception_input.fecha_emision.isoformat()
    )


def test_build_perception_xml_regimen_y_tasa(sample_perception_input):
    xml = build_perception_xml(sample_perception_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.find(f"{{{NS_SAC}}}SUNATPerceptionSystemCode").text == "02"
    assert root.find(f"{{{NS_SAC}}}SUNATPerceptionPercent").text == "2.00"


def test_build_perception_xml_totales(sample_perception_input):
    xml = build_perception_xml(sample_perception_input)
    root = etree.fromstring(xml.encode("utf-8"))
    total_per = root.find(f"{{{NS_CBC}}}TotalInvoiceAmount")
    total_cob = root.find(f"{{{NS_SAC}}}SUNATTotalCashed")
    assert total_per.text == "23.60"
    assert total_per.get("currencyID") == "PEN"
    assert total_cob.text == "1203.60"


def test_build_perception_xml_document_reference(sample_perception_input):
    xml = build_perception_xml(sample_perception_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ref = root.find(f"{{{NS_SAC}}}SUNATPerceptionDocumentReference")
    assert ref is not None
    assert ref.find(f"{{{NS_CBC}}}ID").text == "F001-1"
    info = ref.find(f"{{{NS_SAC}}}SUNATPerceptionInformation")
    assert info is not None
    assert info.find(f"{{{NS_SAC}}}SUNATPerceptionAmount").text == "23.60"
    assert info.find(f"{{{NS_SAC}}}SUNATNetTotalCashed").text == "1203.60"


def test_build_perception_xml_items_vacios_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    per = PerceptionInput(
        serie="P001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="02",
        tasa=Decimal("2.00"),
        total_percibido=Decimal("23.60"),
        total_cobrado=Decimal("1203.60"),
        items=[],
    )
    with pytest.raises(ValidationError, match="items"):
        build_perception_xml(per)


def test_build_perception_xml_serie_invalida_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = PerceptionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_percepcion=Decimal("100"),
        importe_percepcion=Decimal("2"),
        fecha_percepcion=today_lima(),
        importe_total_cobrado=Decimal("102"),
    )
    per = PerceptionInput(
        serie="F001",  # mal: debe empezar con P
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="02",
        tasa=Decimal("2.00"),
        total_percibido=Decimal("2"),
        total_cobrado=Decimal("102"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="serie"):
        build_perception_xml(per)


def test_build_perception_xml_cobrado_mal_calculado_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = PerceptionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_percepcion=Decimal("100"),
        importe_percepcion=Decimal("2"),
        fecha_percepcion=today_lima(),
        importe_total_cobrado=Decimal("99"),  # deberia ser 102
    )
    per = PerceptionInput(
        serie="P001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="02",
        tasa=Decimal("2.00"),
        total_percibido=Decimal("2"),
        total_cobrado=Decimal("99"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="importe_total_cobrado"):
        build_perception_xml(per)


def test_build_perception_xml_suma_items_no_coincide_total_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = PerceptionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_percepcion=Decimal("100"),
        importe_percepcion=Decimal("2"),
        fecha_percepcion=today_lima(),
        importe_total_cobrado=Decimal("102"),
    )
    per = PerceptionInput(
        serie="P001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="02",
        tasa=Decimal("2.00"),
        total_percibido=Decimal("5"),  # no coincide con sum(items) = 2
        total_cobrado=Decimal("102"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="total_percibido"):
        build_perception_xml(per)


def test_build_perception_xml_moneda_extranjera_con_tipo_cambio_ok():
    emisor = Party(
        tipo_doc="6", numero_doc="20000000001", razon_social="X", ubigeo="150101"
    )
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = PerceptionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=date(2026, 5, 1),
        moneda="USD",
        total=Decimal("100"),
        fecha_pago=date(2026, 5, 10),
        importe_sin_percepcion=Decimal("100"),
        importe_percepcion=Decimal("2"),
        fecha_percepcion=date(2026, 5, 10),
        importe_total_cobrado=Decimal("102"),
        tipo_cambio=Decimal("3.752"),
        tipo_cambio_fecha=date(2026, 5, 10),
    )
    per = PerceptionInput(
        serie="P001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="02",
        tasa=Decimal("2.00"),
        total_percibido=Decimal("2"),
        total_cobrado=Decimal("102"),
        items=[item],
    )
    xml = build_perception_xml(per)
    root = etree.fromstring(xml.encode("utf-8"))
    exch = root.find(
        f"{{{NS_SAC}}}SUNATPerceptionDocumentReference"
        f"/{{{NS_SAC}}}SUNATPerceptionInformation"
        f"/{{{NS_CAC}}}ExchangeRate"
    )
    assert exch is not None
    assert exch.find(f"{{{NS_CBC}}}SourceCurrencyCode").text == "USD"
