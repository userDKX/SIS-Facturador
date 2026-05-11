import os
from datetime import date
from decimal import Decimal

import pytest


def _has_beta_envs() -> bool:
    return all(
        [
            os.environ.get("CERT_PFX_BASE64"),
            os.environ.get("CERT_PASSWORD"),
            os.environ.get("SUNAT_RUC"),
            os.environ.get("SUNAT_USER"),
            os.environ.get("SUNAT_PASSWORD"),
        ]
    )


@pytest.fixture(scope="session")
def has_beta_envs() -> bool:
    return _has_beta_envs()


@pytest.fixture
def sample_invoice_input():
    """InvoiceInput valido para tests unit (no toca SUNAT)."""
    from pe_invoicing import InvoiceInput, InvoiceLine, Party

    emisor = Party(
        tipo_doc="6",
        numero_doc="20000000001",
        razon_social="EMPRESA TEST SAC",
        direccion="AV TEST 123 LIMA LIMA",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc="6",
        numero_doc="20100070970",
        razon_social="CLIENTE TEST SAC",
        direccion="AV CLIENTE 456",
    )
    lines = [
        InvoiceLine(
            codigo="P001",
            descripcion="PRODUCTO TEST",
            unidad="NIU",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            igv_afectacion="10",
        ),
    ]
    return InvoiceInput(
        serie="F001",
        numero=1,
        fecha_emision=date(2026, 5, 4),
        moneda="PEN",
        emisor=emisor,
        receptor=receptor,
        lines=lines,
    )


@pytest.fixture
def sample_creditnote_input():
    """CreditNoteInput valido para tests unit (no toca SUNAT)."""
    from pe_invoicing import (
        CreditNoteInput,
        InvoiceLine,
        Party,
        ReferenciaDoc,
    )

    emisor = Party(
        tipo_doc="6",
        numero_doc="20000000001",
        razon_social="EMPRESA TEST SAC",
        direccion="AV TEST 123 LIMA LIMA",
        ubigeo="150101",
    )
    receptor = Party(
        tipo_doc="6",
        numero_doc="20100070970",
        razon_social="CLIENTE TEST SAC",
        direccion="AV CLIENTE 456",
    )
    lines = [
        InvoiceLine(
            codigo="P001",
            descripcion="PRODUCTO TEST",
            unidad="NIU",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            igv_afectacion="10",
        ),
    ]
    return CreditNoteInput(
        serie="FC01",
        numero=1,
        fecha_emision=date(2026, 5, 10),
        moneda="PEN",
        motivo_codigo="01",
        motivo_descripcion="ANULACION DE LA OPERACION",
        referencia=ReferenciaDoc(tipo_doc="01", serie="F001", numero=1),
        emisor=emisor,
        receptor=receptor,
        lines=lines,
    )


@pytest.fixture
def sample_despatchadvice_input():
    """DespatchAdviceInput valido para tests unit — modalidad privada (no toca SUNAT)."""
    from pe_invoicing import (
        Conductor,
        DespatchAdviceInput,
        DireccionTraslado,
        GRLine,
        Party,
        Vehiculo,
    )

    emisor = Party(
        tipo_doc="6",
        numero_doc="20000000001",
        razon_social="EMPRESA TEST SAC",
        direccion="AV TEST 123 LIMA",
        ubigeo="150101",
    )
    destinatario = Party(
        tipo_doc="6",
        numero_doc="20100070970",
        razon_social="CLIENTE TEST SAC",
        direccion="AV CLIENTE 456",
    )
    lines = [
        GRLine(
            codigo="P001",
            descripcion="PRODUCTO TEST",
            unidad="NIU",
            cantidad=Decimal("5"),
        ),
    ]
    return DespatchAdviceInput(
        serie="T001",
        numero=1,
        fecha_emision=date(2026, 5, 11),
        motivo_traslado="01",
        motivo_descripcion="VENTA",
        modalidad="02",
        peso_bruto_total=Decimal("10.00"),
        peso_bruto_unidad="KGM",
        emisor=emisor,
        destinatario=destinatario,
        partida=DireccionTraslado(
            ubigeo="150101", direccion="AV TEST 123 LIMA", cod_local="0000"
        ),
        llegada=DireccionTraslado(ubigeo="150122", direccion="AV CLIENTE 456"),
        lines=lines,
        numero_bultos=2,
        conductor=Conductor(
            tipo_doc="1",
            numero_doc="12345678",
            nombres="JUAN",
            apellidos="PEREZ",
            licencia="Q12345678",
        ),
        vehiculo=Vehiculo(placa="ABC123"),
    )
