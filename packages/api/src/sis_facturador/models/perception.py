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


class Perception(Base):
    """Comprobante de percepcion del IGV (tipo 40).

    Solo agentes de percepcion designados por SUNAT pueden emitir este
    documento. Unicidad por `(ruc_emisor, serie, numero)`.
    """

    __tablename__ = "perceptions"
    __table_args__ = (
        UniqueConstraint(
            "ruc_emisor",
            "serie",
            "numero",
            name="uq_perceptions_doc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    ruc_emisor: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False, default="40")
    serie: Mapped[str] = mapped_column(String(4), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")

    receptor_tipo_doc: Mapped[str] = mapped_column(String(1), nullable=False)
    receptor_numero_doc: Mapped[str] = mapped_column(String(15), nullable=False)
    receptor_razon_social: Mapped[str] = mapped_column(String(250), nullable=False)

    # Catalogo SUNAT 22: 01 combustible, 02 venta interna, 03 importacion.
    regimen: Mapped[str] = mapped_column(String(2), nullable=False)
    tasa: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    total_percibido: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_cobrado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
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

    items: Mapped[list["PerceptionItem"]] = relationship(
        back_populates="perception",
        cascade="all, delete-orphan",
        order_by="PerceptionItem.id",
    )


class PerceptionItem(Base):
    """Cada cobro percibido dentro de un comprobante de percepcion."""

    __tablename__ = "perception_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    perception_id: Mapped[int] = mapped_column(
        ForeignKey("perceptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ref_tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False)
    ref_serie: Mapped[str] = mapped_column(String(4), nullable=False)
    ref_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    ref_moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")
    ref_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    correlativo_pago: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    importe_sin_percepcion: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    importe_percepcion: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_percepcion: Mapped[date] = mapped_column(Date, nullable=False)
    importe_total_cobrado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    tipo_cambio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    tipo_cambio_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)

    perception: Mapped[Perception] = relationship(back_populates="items")
