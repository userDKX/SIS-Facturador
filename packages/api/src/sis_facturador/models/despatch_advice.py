from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from sis_facturador.database import Base


class DespatchAdvice(Base):
    """Guia de remision remitente (tipo 09).

    No tiene valores monetarios (sin subtotal/igv/total).
    """

    __tablename__ = "despatch_advices"
    __table_args__ = (
        UniqueConstraint(
            "ruc_emisor",
            "serie",
            "numero",
            name="uq_despatch_advices_doc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruc_emisor: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False, default="09")
    serie: Mapped[str] = mapped_column(String(4), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)

    motivo_traslado: Mapped[str] = mapped_column(String(2), nullable=False)
    motivo_descripcion: Mapped[str] = mapped_column(String(250), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(2), nullable=False)
    peso_bruto_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    peso_bruto_unidad: Mapped[str] = mapped_column(String(5), nullable=False, default="KGM")
    numero_bultos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    destinatario_tipo_doc: Mapped[str] = mapped_column(String(1), nullable=False)
    destinatario_numero_doc: Mapped[str] = mapped_column(String(15), nullable=False)
    destinatario_razon_social: Mapped[str] = mapped_column(String(250), nullable=False)

    partida_ubigeo: Mapped[str] = mapped_column(String(6), nullable=False)
    partida_direccion: Mapped[str] = mapped_column(String(500), nullable=False)
    partida_cod_local: Mapped[str | None] = mapped_column(String(4), nullable=True)
    llegada_ubigeo: Mapped[str] = mapped_column(String(6), nullable=False)
    llegada_direccion: Mapped[str] = mapped_column(String(500), nullable=False)
    llegada_cod_local: Mapped[str | None] = mapped_column(String(4), nullable=True)

    transportista_ruc: Mapped[str | None] = mapped_column(String(11), nullable=True)
    transportista_razon_social: Mapped[str | None] = mapped_column(String(250), nullable=True)
    conductor_tipo_doc: Mapped[str | None] = mapped_column(String(1), nullable=True)
    conductor_numero_doc: Mapped[str | None] = mapped_column(String(15), nullable=True)
    conductor_licencia: Mapped[str | None] = mapped_column(String(15), nullable=True)
    vehiculo_placa: Mapped[str | None] = mapped_column(String(10), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    sunat_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sunat_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    xml_signed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cdr_xml_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hash_signature: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
