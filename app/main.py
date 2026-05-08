import logging
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import invoices as invoices_router
from app.security.cert_loader import load_cert

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SIS Facturador",
    description="API de facturacion electronica SUNAT",
    version="0.1.0",
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


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/health/cert")
def health_cert() -> dict:
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
