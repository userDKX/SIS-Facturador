from datetime import date
from decimal import Decimal

import pytest
from lxml import etree
from sunat_py import Party, ValidationError, today_lima
from sunat_py.ubl.builder import build_retention_xml
from sunat_py.ubl.models import RetentionDocReference, RetentionInput

NS_RET = "urn:sunat:names:specification:ubl:peru:schema:xsd:Retention-1"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_SAC = "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1"


def test_build_retention_xml_root(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.tag == f"{{{NS_RET}}}Retention"


def test_build_retention_xml_ubl_version_y_customization(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.find(f"{{{NS_CBC}}}UBLVersionID").text == "2.0"
    assert root.find(f"{{{NS_CBC}}}CustomizationID").text == "1.0"


def test_build_retention_xml_id_y_fecha(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.find(f"{{{NS_CBC}}}ID").text == "R001-1"
    assert (
        root.find(f"{{{NS_CBC}}}IssueDate").text
        == sample_retention_input.fecha_emision.isoformat()
    )


def test_build_retention_xml_agent_party(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    agent = root.find(f"{{{NS_CAC}}}AgentParty")
    assert agent is not None
    party_id = agent.find(f"{{{NS_CAC}}}PartyIdentification/{{{NS_CBC}}}ID")
    assert party_id.text == "20000000001"
    assert party_id.get("schemeID") == "6"


def test_build_retention_xml_receiver_party(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    receiver = root.find(f"{{{NS_CAC}}}ReceiverParty")
    assert receiver is not None
    party_id = receiver.find(f"{{{NS_CAC}}}PartyIdentification/{{{NS_CBC}}}ID")
    assert party_id.text == "20100070970"


def test_build_retention_xml_regimen_y_tasa(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    assert root.find(f"{{{NS_SAC}}}SUNATRetentionSystemCode").text == "01"
    assert root.find(f"{{{NS_SAC}}}SUNATRetentionPercent").text == "3.00"


def test_build_retention_xml_totales(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    total_ret = root.find(f"{{{NS_CBC}}}TotalInvoiceAmount")
    total_pag = root.find(f"{{{NS_SAC}}}SUNATTotalPaid")
    assert total_ret.text == "35.40"
    assert total_ret.get("currencyID") == "PEN"
    assert total_pag.text == "1144.60"


def test_build_retention_xml_document_reference(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ref = root.find(f"{{{NS_SAC}}}SUNATRetentionDocumentReference")
    assert ref is not None
    assert ref.find(f"{{{NS_CBC}}}ID").text == "F001-1"
    assert ref.find(f"{{{NS_CBC}}}ID").get("schemeID") == "01"
    info = ref.find(f"{{{NS_SAC}}}SUNATRetentionInformation")
    assert info is not None
    assert info.find(f"{{{NS_SAC}}}SUNATRetentionAmount").text == "35.40"
    assert info.find(f"{{{NS_SAC}}}SUNATNetTotalPaid").text == "1144.60"


def test_build_retention_xml_extension_content_vacio(sample_retention_input):
    xml = build_retention_xml(sample_retention_input)
    root = etree.fromstring(xml.encode("utf-8"))
    ext = root.find(
        f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
    )
    assert ext is not None and len(ext) == 0


def test_build_retention_xml_items_vacios_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    ret = RetentionInput(
        serie="R001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("35.40"),
        total_pagado=Decimal("1144.60"),
        items=[],
    )
    with pytest.raises(ValidationError, match="items"):
        build_retention_xml(ret)


def test_build_retention_xml_serie_invalida_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = RetentionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_retencion=Decimal("100"),
        importe_retencion=Decimal("3"),
        fecha_retencion=today_lima(),
        importe_neto_pagado=Decimal("97"),
    )
    ret = RetentionInput(
        serie="F001",  # mal: debe empezar con R
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("3"),
        total_pagado=Decimal("97"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="serie"):
        build_retention_xml(ret)


def test_build_retention_xml_neto_mal_calculado_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = RetentionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_retencion=Decimal("100"),
        importe_retencion=Decimal("3"),
        fecha_retencion=today_lima(),
        importe_neto_pagado=Decimal("90"),  # deberia ser 97
    )
    ret = RetentionInput(
        serie="R001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("3"),
        total_pagado=Decimal("90"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="importe_neto_pagado"):
        build_retention_xml(ret)


def test_build_retention_xml_tipo_doc_invalido_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    # Forzamos tipo_doc invalido para retencion (SUNAT solo acepta 01)
    item = RetentionDocReference(
        serie="B001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_retencion=Decimal("100"),
        importe_retencion=Decimal("3"),
        fecha_retencion=today_lima(),
        importe_neto_pagado=Decimal("97"),
        tipo_doc="01",
    )
    # Mutamos el tipo_doc via __dict__ (dataclass frozen) — solo en test
    object.__setattr__(item, "tipo_doc", "03")
    ret = RetentionInput(
        serie="R001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("3"),
        total_pagado=Decimal("97"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="tipo_doc"):
        build_retention_xml(ret)


def test_build_retention_xml_moneda_extranjera_sin_tipo_cambio_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = RetentionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="USD",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_retencion=Decimal("100"),
        importe_retencion=Decimal("3"),
        fecha_retencion=today_lima(),
        importe_neto_pagado=Decimal("97"),
        # tipo_cambio omitido a proposito
    )
    ret = RetentionInput(
        serie="R001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("3"),
        total_pagado=Decimal("97"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="tipo_cambio"):
        build_retention_xml(ret)


def test_build_retention_xml_suma_items_no_coincide_total_falla():
    emisor = Party(tipo_doc="6", numero_doc="20000000001", razon_social="X")
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = RetentionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=today_lima(),
        moneda="PEN",
        total=Decimal("100"),
        fecha_pago=today_lima(),
        importe_sin_retencion=Decimal("100"),
        importe_retencion=Decimal("3"),
        fecha_retencion=today_lima(),
        importe_neto_pagado=Decimal("97"),
    )
    ret = RetentionInput(
        serie="R001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("5"),  # no coincide con sum(items) = 3
        total_pagado=Decimal("97"),
        items=[item],
    )
    with pytest.raises(ValidationError, match="total_retenido"):
        build_retention_xml(ret)


def test_build_retention_xml_moneda_extranjera_con_tipo_cambio_ok():
    emisor = Party(
        tipo_doc="6", numero_doc="20000000001", razon_social="X", ubigeo="150101"
    )
    receptor = Party(tipo_doc="6", numero_doc="20100070970", razon_social="Y")
    item = RetentionDocReference(
        serie="F001",
        numero=1,
        fecha_emision=date(2026, 5, 1),
        moneda="USD",
        total=Decimal("100"),
        fecha_pago=date(2026, 5, 10),
        importe_sin_retencion=Decimal("100"),
        importe_retencion=Decimal("3"),
        fecha_retencion=date(2026, 5, 10),
        importe_neto_pagado=Decimal("97"),
        tipo_cambio=Decimal("3.752"),
        tipo_cambio_fecha=date(2026, 5, 10),
    )
    ret = RetentionInput(
        serie="R001",
        numero=1,
        fecha_emision=today_lima(),
        emisor=emisor,
        receptor=receptor,
        regimen="01",
        tasa=Decimal("3.00"),
        total_retenido=Decimal("3"),
        total_pagado=Decimal("97"),
        items=[item],
    )
    xml = build_retention_xml(ret)
    root = etree.fromstring(xml.encode("utf-8"))
    exch = root.find(
        f"{{{NS_SAC}}}SUNATRetentionDocumentReference"
        f"/{{{NS_SAC}}}SUNATRetentionInformation"
        f"/{{{NS_CAC}}}ExchangeRate"
    )
    assert exch is not None
    assert exch.find(f"{{{NS_CBC}}}SourceCurrencyCode").text == "USD"
    assert exch.find(f"{{{NS_CBC}}}TargetCurrencyCode").text == "PEN"
    assert exch.find(f"{{{NS_CBC}}}CalculationRate").text == "3.75"
