from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis_facturador.schemas.invoice import PartyIn

MotivoTraslado = Literal[
    "01",  # Venta
    "02",  # Compra
    "04",  # Traslado entre establecimientos de la misma empresa
    "08",  # Importacion
    "09",  # Exportacion
    "13",  # Otros
    "18",  # Traslado emisor itinerante CP
    "19",  # Traslado a zona primaria
]


class DireccionIn(BaseModel):
    """Punto de partida o llegada del traslado.

    ubigeo: codigo INEI de 6 digitos (ej. "150101" Lima Cercado).
    cod_local: codigo del establecimiento anexo SUNAT (4 digitos).
        "0000" = casa matriz; "0001"+ = anexos. SUNAT lo exige cuando el
        motivo de traslado es "04" (entre establecimientos misma empresa).
    """

    ubigeo: Annotated[str, Field(min_length=6, max_length=6)]
    direccion: Annotated[str, Field(min_length=1, max_length=500)]
    cod_local: Annotated[str, Field(max_length=4)] = ""


class TransportistaIn(BaseModel):
    """Empresa transportista (solo para modalidad "01" transporte publico).

    numero_doc debe ser el RUC de 11 digitos del transportista registrado en MTC.
    """

    numero_doc: Annotated[str, Field(min_length=11, max_length=11)]
    razon_social: Annotated[str, Field(min_length=1, max_length=250)]


class ConductorIn(BaseModel):
    """Conductor del vehiculo (requerido para modalidad "02" transporte privado).

    tipo_doc (Catalogo SUNAT 06): tipicamente "1" (DNI).
    licencia: numero de licencia de conducir vigente. SUNAT lo exige siempre
    para modalidad privada (error 2572 si falta).
    """

    tipo_doc: Annotated[str, Field(min_length=1, max_length=1)]
    numero_doc: Annotated[str, Field(min_length=1, max_length=15)]
    nombres: Annotated[str, Field(min_length=1, max_length=100)]
    apellidos: Annotated[str, Field(min_length=1, max_length=100)]
    licencia: Annotated[str, Field(min_length=1, max_length=15)]


class VehiculoIn(BaseModel):
    placa: Annotated[str, Field(min_length=1, max_length=10)]


class GRLineIn(BaseModel):
    """Linea de detalle de la guia de remision (sin valores monetarios)."""

    codigo: Annotated[str, Field(min_length=1, max_length=30)]
    descripcion: Annotated[str, Field(min_length=1, max_length=500)]
    unidad: Annotated[str, Field(min_length=1, max_length=10)]
    cantidad: Annotated[Decimal, Field(gt=0)]


_GR_PRIVADO_EXAMPLE = {
    "serie": "T001",
    "numero": 1,
    "fecha_emision": "2026-05-11",
    "motivo_traslado": "01",
    "motivo_descripcion": "VENTA",
    "modalidad": "02",
    "peso_bruto_total": "10.00",
    "peso_bruto_unidad": "KGM",
    "numero_bultos": 2,
    "destinatario": {
        "tipo_doc": "6",
        "numero_doc": "20512345678",
        "razon_social": "CLIENTE EJEMPLO SAC",
        "direccion": "AV. LIMA 456, MIRAFLORES",
    },
    "partida": {"ubigeo": "150101", "direccion": "AV. PRINCIPAL 123, LIMA", "cod_local": "0000"},
    "llegada": {"ubigeo": "150122", "direccion": "AV. LIMA 456, MIRAFLORES"},
    "conductor": {
        "tipo_doc": "1",
        "numero_doc": "12345678",
        "nombres": "JUAN",
        "apellidos": "PEREZ",
        "licencia": "Q12345678",
    },
    "vehiculo": {"placa": "ABC123"},
    "lines": [
        {
            "codigo": "PROD001",
            "descripcion": "Producto ejemplo",
            "unidad": "NIU",
            "cantidad": "5.00",
        },
    ],
}

_GR_PUBLICO_EXAMPLE = {
    "serie": "T001",
    "numero": 2,
    "fecha_emision": "2026-05-11",
    "motivo_traslado": "01",
    "motivo_descripcion": "VENTA",
    "modalidad": "01",
    "peso_bruto_total": "25.50",
    "peso_bruto_unidad": "KGM",
    "destinatario": {
        "tipo_doc": "6",
        "numero_doc": "20512345678",
        "razon_social": "CLIENTE EJEMPLO SAC",
        "direccion": "AV. LIMA 456, MIRAFLORES",
    },
    "partida": {"ubigeo": "150101", "direccion": "AV. PRINCIPAL 123, LIMA", "cod_local": "0000"},
    "llegada": {"ubigeo": "150122", "direccion": "AV. LIMA 456, MIRAFLORES"},
    "transportista": {"numero_doc": "20100123456", "razon_social": "TRANSPORTES SAC"},
    "lines": [
        {
            "codigo": "PROD001",
            "descripcion": "Producto ejemplo",
            "unidad": "NIU",
            "cantidad": "10.00",
        },
    ],
}


class DespatchAdviceCreate(BaseModel):
    """Payload para emitir una guia de remision remitente (tipo 09).

    La serie debe tener prefijo T (ej. T001, T002).

    Reglas de modalidad:
      * modalidad="01" (transporte publico) → `transportista` es obligatorio.
      * modalidad="02" (transporte privado) → `conductor` y `vehiculo` son obligatorios.

    `motivo_traslado` es del catalogo SUNAT 20.
    `peso_bruto_unidad` es tipicamente "KGM" (kilogramos).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [_GR_PRIVADO_EXAMPLE, _GR_PUBLICO_EXAMPLE],
        }
    )

    serie: Annotated[str, Field(min_length=4, max_length=4, pattern=r"^T[A-Z0-9]{3}$")]
    numero: Annotated[int, Field(gt=0)]
    fecha_emision: date
    motivo_traslado: MotivoTraslado
    motivo_descripcion: Annotated[str, Field(min_length=1, max_length=250)]
    modalidad: Literal["01", "02"]
    peso_bruto_total: Annotated[Decimal, Field(gt=0)]
    peso_bruto_unidad: str = "KGM"
    destinatario: PartyIn
    partida: DireccionIn
    llegada: DireccionIn
    lines: Annotated[list[GRLineIn], Field(min_length=1)]
    numero_bultos: int | None = None
    transportista: TransportistaIn | None = None
    conductor: ConductorIn | None = None
    vehiculo: VehiculoIn | None = None

    @model_validator(mode="after")
    def _validate_modalidad(self) -> "DespatchAdviceCreate":
        if self.modalidad == "01" and not self.transportista:
            raise ValueError(
                "Para modalidad '01' (transporte publico) se requiere 'transportista'."
            )
        if self.modalidad == "02" and not self.conductor:
            raise ValueError("Para modalidad '02' (transporte privado) se requiere 'conductor'.")
        if self.modalidad == "02" and not self.vehiculo:
            raise ValueError("Para modalidad '02' (transporte privado) se requiere 'vehiculo'.")
        return self


class DespatchAdviceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "ruc_emisor": "20XXXXXXXXX",
                "tipo_doc": "09",
                "serie": "T001",
                "numero": 1,
                "fecha_emision": "2026-05-11",
                "motivo_traslado": "01",
                "motivo_descripcion": "VENTA",
                "modalidad": "02",
                "peso_bruto_total": "10.00",
                "peso_bruto_unidad": "KGM",
                "numero_bultos": 2,
                "destinatario_tipo_doc": "6",
                "destinatario_numero_doc": "20512345678",
                "destinatario_razon_social": "CLIENTE EJEMPLO SAC",
                "partida_ubigeo": "150101",
                "partida_direccion": "AV. PRINCIPAL 123, LIMA",
                "partida_cod_local": "0000",
                "llegada_ubigeo": "150122",
                "llegada_direccion": "AV. LIMA 456, MIRAFLORES",
                "llegada_cod_local": None,
                "transportista_ruc": None,
                "transportista_razon_social": None,
                "conductor_tipo_doc": "1",
                "conductor_numero_doc": "12345678",
                "conductor_licencia": "Q12345678",
                "vehiculo_placa": "ABC123",
                "status": "accepted",
                "sunat_code": "0",
                "sunat_description": "La Guia de Remision T001-1 ha sido aceptada",
                "xml_signed_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/xml/20XXXXXXXXX-09-T001-1.xml",
                "cdr_xml_url": "https://xxx.supabase.co/storage/v1/object/public/comprobantes/cdr/R-20XXXXXXXXX-09-T001-1.xml",
                "error_message": None,
            }
        },
    )

    id: int
    ruc_emisor: str
    tipo_doc: str
    serie: str
    numero: int
    fecha_emision: date
    motivo_traslado: str
    motivo_descripcion: str
    modalidad: str
    peso_bruto_total: Decimal
    peso_bruto_unidad: str
    numero_bultos: int | None
    destinatario_tipo_doc: str
    destinatario_numero_doc: str
    destinatario_razon_social: str
    partida_ubigeo: str
    partida_direccion: str
    partida_cod_local: str | None
    llegada_ubigeo: str
    llegada_direccion: str
    llegada_cod_local: str | None
    transportista_ruc: str | None
    transportista_razon_social: str | None
    conductor_tipo_doc: str | None
    conductor_numero_doc: str | None
    conductor_licencia: str | None
    vehiculo_placa: str | None
    status: str
    sunat_code: str | None
    sunat_description: str | None
    xml_signed_url: str | None
    cdr_xml_url: str | None
    error_message: str | None
