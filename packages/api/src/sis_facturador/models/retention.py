from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sis_facturador.database import Base


class Retention(Base):
    """Comprobante de retencion del IGV (tipo 20).

    Solo agentes de retencion designados por SUNAT pueden emitir este
    documento. La unicidad esta dada por `(ruc_emisor, serie, numero)`.
    """

    __tablename__ = "retentions"
    __table_args__ = (
        UniqueConstraint(
            "ruc_emisor",
            "serie",
            "numero",
            name="uq_retentions_doc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    ruc_emisor: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False, default="20")
    serie: Mapped[str] = mapped_column(String(4), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")

    receptor_tipo_doc: Mapped[str] = mapped_column(String(1), nullable=False)
    receptor_numero_doc: Mapped[str] = mapped_column(String(15), nullable=False)
    receptor_razon_social: Mapped[str] = mapped_column(String(250), nullable=False)

    # Catalogo SUNAT 23 — siempre "01".
    regimen: Mapped[str] = mapped_column(String(2), nullable=False, default="01")
    # Tasa aplicada (3.00 vigente, 6.00 historico).
    tasa: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    total_retenido: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    nota: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
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

    items: Mapped[list["RetentionItem"]] = relationship(
        back_populates="retention",
        cascade="all, delete-orphan",
        order_by="RetentionItem.id",
    )


class RetentionItem(Base):
    """Cada pago retenido dentro de un comprobante de retencion.

    Una factura puede aparecer en varios items si hay pagos parciales
    (cada item = un pago, no una factura completa).
    """

    __tablename__ = "retention_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    retention_id: Mapped[int] = mapped_column(
        ForeignKey("retentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Factura referenciada (siempre tipo 01)
    ref_tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False, default="01")
    ref_serie: Mapped[str] = mapped_column(String(4), nullable=False)
    ref_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    ref_moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")
    ref_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Pago
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    correlativo_pago: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    importe_sin_retencion: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    importe_retencion: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_retencion: Mapped[date] = mapped_column(Date, nullable=False)
    importe_neto_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Tipo de cambio (solo si ref_moneda != PEN)
    tipo_cambio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    tipo_cambio_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)

    retention: Mapped[Retention] = relationship(back_populates="items")
