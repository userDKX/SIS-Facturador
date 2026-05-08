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
    from app.ubl.models import InvoiceInput, InvoiceLine, Party

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
