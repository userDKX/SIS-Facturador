"""Wrappers cacheados del SDK que leen settings del servicio.

Mantienen el caso single-tenant simple: una sola carga de cert por proceso,
un solo cliente zeep por proceso. Para multi-tenant (futuro), reemplazar
los caches por estructuras key-by-tenant.
"""

from __future__ import annotations

from functools import lru_cache

from sunat_py import (
    CertBundle,
    build_zeep_client,
    load_cert_from_base64,
)
from zeep import Client

from sis_facturador.config import settings


@lru_cache(maxsize=1)
def get_cert() -> CertBundle:
    """Devuelve el cert cacheado a partir de CERT_PFX_BASE64 + CERT_PASSWORD."""
    return load_cert_from_base64(settings.CERT_PFX_BASE64, settings.CERT_PASSWORD)


@lru_cache(maxsize=1)
def get_sunat_client() -> Client:
    """Cliente zeep contra el billService de SUNAT (factura/boleta/NC/ND/RA/RC).

    Endpoint: `ol-ti-itcpfegem/billService`.
    """
    return build_zeep_client(
        mode=settings.MODE,
        ruc=settings.SUNAT_RUC,
        username=settings.SUNAT_USER,
        password=settings.SUNAT_PASSWORD,
        service="bill",
    )


@lru_cache(maxsize=1)
def get_sunat_client_otroscpe() -> Client:
    """Cliente zeep contra el servicio de otros CPE (retencion / percepcion).

    Endpoint: `ol-ti-itemision-otroscpe-gem/billService`. SUNAT separa
    estos tipos del billService principal; mandar tipo 20/40 al cliente
    base devuelve error 0151.
    """
    return build_zeep_client(
        mode=settings.MODE,
        ruc=settings.SUNAT_RUC,
        username=settings.SUNAT_USER,
        password=settings.SUNAT_PASSWORD,
        service="otroscpe",
    )
