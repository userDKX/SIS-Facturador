import logging
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app import __version__
from app.routers import invoices as invoices_router
from app.security.cert_loader import load_cert

logger = logging.getLogger(__name__)

DESCRIPTION = """
API REST para emitir comprobantes electrónicos a SUNAT (Perú): Factura
(`01`) y Boleta de venta (`03`). Genera UBL 2.1, firma con XMLDSig
RSA-SHA256, envía por SOAP al WS del contribuyente (SEE-DSC) y devuelve el
CDR.

Documentación completa en el [repositorio](https://github.com/dukex57/sis-facturador):

* [`docs/INSTALL.md`](https://github.com/dukex57/sis-facturador/blob/main/docs/INSTALL.md) — instalación local
* [`docs/SUNAT_SETUP.md`](https://github.com/dukex57/sis-facturador/blob/main/docs/SUNAT_SETUP.md) — onboarding del RUC en SUNAT
* [`docs/SIGNING.md`](https://github.com/dukex57/sis-facturador/blob/main/docs/SIGNING.md) — detalles de la firma XMLDSig
* [`docs/TROUBLESHOOTING.md`](https://github.com/dukex57/sis-facturador/blob/main/docs/TROUBLESHOOTING.md) — diagnóstico de errores
"""

TAGS_METADATA = [
    {
        "name": "health",
        "description": "Healthchecks del servicio y del certificado digital.",
    },
    {
        "name": "invoices",
        "description": (
            "Emisión y consulta de comprobantes electrónicos. "
            "POST `/v1/invoices` arma el UBL, firma, envía a SUNAT y persiste."
        ),
    },
]

app = FastAPI(
    title="SIS Facturador",
    description=DESCRIPTION,
    version=__version__,
    contact={
        "name": "Luis Luza M.",
        "url": "https://github.com/dukex57/sis-facturador",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/dukex57/sis-facturador/blob/main/LICENSE",
    },
    openapi_tags=TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get(
    "/v1/health",
    tags=["health"],
    summary="Liveness check",
    response_description="Servicio arriba.",
)
def health() -> dict[str, str]:
    """Devuelve `{'status': 'ok'}` si el proceso está corriendo. No verifica
    dependencias (BD, SUNAT) — para eso usa los healthchecks específicos."""
    return {"status": "ok"}


@app.get(
    "/v1/health/cert",
    tags=["health"],
    summary="Validez del certificado digital",
    response_description="Metadata del cert cargado y si está vigente.",
    responses={
        500: {
            "description": "El cert no se pudo cargar (CERT_PFX_BASE64 mal configurado o password incorrecta).",
        },
    },
)
def health_cert() -> dict:
    """Carga el `.pfx` desde `CERT_PFX_BASE64`, extrae metadata del cert
    X.509 y reporta si está vigente.

    Útil después de un deploy para confirmar que el cert quedó bien
    instalado antes de empezar a emitir."""
    try:
        bundle = load_cert()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo cargar el cert: {exc}") from exc

    expires_at = bundle.certificate.not_valid_after_utc
    now = datetime.now(UTC)
    return {
        "common_name": bundle.common_name,
        "serial": bundle.serial_hex,
        "not_valid_before": bundle.certificate.not_valid_before_utc.isoformat(),
        "not_valid_after": expires_at.isoformat(),
        "expired": expires_at < now,
    }


app.include_router(
    invoices_router.router,
    prefix="/v1/invoices",
    tags=["invoices"],
)
