"""Cliente REST para la Nueva GRE (Guia de Remision Electronica) de SUNAT.

Flujo:
    1. POST token   -> api-seguridad.sunat.gob.pe   (OAuth2 password grant)
    2. POST envio   -> api-cpe.sunat.gob.pe         (ZIP en base64 + hash SHA256)
    3. GET  consulta-> api-cpe.sunat.gob.pe         (polling por numTicket)

api-cpe.sunat.gob.pe sirve tanto prod como beta — el ambiente lo determinan
las credenciales OAuth2 (client_id/secret) del contribuyente.
El path param del POST es el filename SIN extension `.zip`.
"""

from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass

import requests

GRE_API_HOST = "https://api-cpe.sunat.gob.pe"


@dataclass(frozen=True)
class GreResult:
    status: str  # "accepted" | "accepted_with_obs" | "rejected" | "error"
    code: str
    description: str
    cdr_zip: bytes | None = None


def get_gre_token(
    *,
    client_id: str,
    client_secret: str,
    ruc: str,
    username: str,
    password: str,
) -> str:
    """Obtiene access token OAuth2 para la API GRE.

    username: usuario SOL sin RUC (solo el sufijo, ej. "FACSIS11").
    Internamente se concatena como {ruc}{username}.
    """
    url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    resp = requests.post(
        url,
        data={
            "grant_type": "password",
            "scope": "https://api-cpe.sunat.gob.pe",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": f"{ruc}{username}",
            "password": password,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_gre(
    *,
    token: str,
    ruc: str,
    zip_bytes: bytes,
    filename_base: str,
    poll_retries: int = 10,
    poll_interval: float = 3.0,
) -> GreResult:
    """Envia la GRE firmada y espera el resultado del CDR.

    filename_base: nombre sin extension, ej. "20495184120-09-T001-1".
    """
    zip_name = f"{filename_base}.zip"
    arc_b64 = base64.b64encode(zip_bytes).decode("utf-8")
    hash_zip = hashlib.sha256(zip_bytes).hexdigest()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Envio. El path param es filename SIN extension (.zip va dentro del body como nomArchivo).
    send_url = f"{GRE_API_HOST}/v1/contribuyente/gem/comprobantes/{filename_base}"
    resp = requests.post(
        send_url,
        json={"archivo": {"nomArchivo": zip_name, "arcGreZip": arc_b64, "hashZip": hash_zip}},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    ticket = resp.json()["numTicket"]

    # Polling
    poll_url = f"{GRE_API_HOST}/v1/contribuyente/gem/comprobantes/envios/{ticket}"
    for _ in range(poll_retries):
        time.sleep(poll_interval)
        r = requests.get(poll_url, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        cod = str(data.get("codRespuesta", ""))
        if cod == "98":
            continue  # en proceso
        cdr_zip = base64.b64decode(data["arcCdr"]) if data.get("arcCdr") else None
        # Rechazo pre-CDR: SUNAT pone el detalle del error en `error.desError`
        # (con `numError` = codigo de error SUNAT). Ese caso no trae arcCdr.
        err = data.get("error") if isinstance(data.get("error"), dict) else None
        err_msg = None
        if err:
            num = err.get("numError")
            desc = err.get("desError") or err.get("message")
            err_msg = f"{num}: {desc}" if num and desc else (desc or str(err))
        if cod == "0":
            return GreResult(status="accepted", code=cod, description="Aceptado", cdr_zip=cdr_zip)
        if cod == "098":
            desc = data.get("desRespuesta", "Aceptado con observaciones")
            return GreResult(
                status="accepted_with_obs", code=cod, description=desc, cdr_zip=cdr_zip
            )
        desc = data.get("desRespuesta") or err_msg or "Rechazado"
        return GreResult(status="rejected", code=cod, description=desc, cdr_zip=cdr_zip)

    return GreResult(
        status="error", code="TIMEOUT", description="Sin respuesta de SUNAT tras reintentos"
    )
