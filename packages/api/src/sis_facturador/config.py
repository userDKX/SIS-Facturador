from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

SUNAT_WSDL_BETA = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl"
SUNAT_WSDL_PROD = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MODE: Literal["beta", "prod"] = "beta"

    DATABASE_URL: str

    # Storage: "local" (filesystem en LOCAL_STORAGE_DIR) o "supabase" (cloud).
    # Vercel requiere "supabase" porque el filesystem es efimero.
    STORAGE_BACKEND: Literal["local", "supabase"] = "local"
    LOCAL_STORAGE_DIR: str = ""  # vacio = <repo>/storage

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "comprobantes"

    SUNAT_RUC: str
    SUNAT_USER: str
    SUNAT_PASSWORD: str

    CERT_PFX_BASE64: str
    CERT_PASSWORD: str

    # Credenciales API GRE (Nueva Guia de Remision Electronica).
    # Se obtienen en SUNAT SOL > Credenciales API SUNAT y son independientes
    # del usuario SOL / certificado. Requeridas solo para emitir tipo 09.
    GRE_CLIENT_ID: str = ""
    GRE_CLIENT_SECRET: str = ""

    @property
    def sunat_wsdl(self) -> str:
        return SUNAT_WSDL_PROD if self.MODE == "prod" else SUNAT_WSDL_BETA

    @property
    def sunat_username(self) -> str:
        return f"{self.SUNAT_RUC}{self.SUNAT_USER}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
