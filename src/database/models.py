from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from sqlalchemy import String, Integer, BigInteger, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from pydantic import BaseModel as PydanticBaseModel
import uuid


class Base(DeclarativeBase):
    """Classe base para todos os modelos."""

    pass


class OrderStatus(str, Enum):
    """Status possíveis de um pedido."""

    PENDING = "pending"  # Aguardando pagamento
    PAID = "paid"  # Pago, aguardando entrega
    PROCESSING = "processing"  # Processando entrega
    DELIVERED = "delivered"  # Entregue
    CANCELLED = "cancelled"  # Cancelado
    REFUNDED = "refunded"  # Reembolsado
    EXPIRED = "expired"  # Expirado


class TicketStatus(str, Enum):
    """Status possíveis de um ticket."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    CLOSED = "closed"


class PaymentMethod(str, Enum):
    """Métodos de pagamento disponíveis."""

    PIX = "pix"


def generate_short_uuid() -> str:
    """Gera um UUID curto de 8 caracteres."""
    return str(uuid.uuid4())[:8].upper()


class User(Base):
    """Modelo de usuário."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    discord_name: Mapped[str] = mapped_column(String(100), nullable=False)
    roblox_username: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    roblox_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    total_robux_bought: Mapped[int] = mapped_column(Integer, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "discord_id": self.discord_id,
            "discord_name": self.discord_name,
            "roblox_username": self.roblox_username,
            "roblox_id": self.roblox_id,
            "total_spent": self.total_spent,
            "total_robux_bought": self.total_robux_bought,
            "orders_count": self.orders_count,
            "is_banned": self.is_banned,
            "is_vip": self.is_vip,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Order(Base):
    """Modelo de pedido."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True, default=generate_short_uuid
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    roblox_username: Mapped[str] = mapped_column(String(50), nullable=False)
    roblox_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    robux_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    price_brl: Mapped[float] = mapped_column(Float, nullable=False)
    gamepass_price: Mapped[int] = mapped_column(Integer, nullable=False)
    gamepass_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    gamepass_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=OrderStatus.PENDING.value, index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.PIX.value
    )
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    pix_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pix_qrcode: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)
    ticket_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "roblox_username": self.roblox_username,
            "roblox_id": self.roblox_id,
            "robux_amount": self.robux_amount,
            "price_brl": self.price_brl,
            "gamepass_price": self.gamepass_price,
            "gamepass_id": self.gamepass_id,
            "gamepass_url": self.gamepass_url,
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_id": self.payment_id,
            "pix_code": self.pix_code,
            "pix_qrcode": self.pix_qrcode,
            "coupon_code": self.coupon_code,
            "discount_percent": self.discount_percent,
            "ticket_channel_id": self.ticket_channel_id,
            "message_id": self.message_id,
            "notes": self.notes or [],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "paid_at": self.paid_at,
            "delivered_at": self.delivered_at,
            "expires_at": self.expires_at,
        }


class Ticket(Base):
    """Modelo de ticket/carrinho."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True, default=generate_short_uuid
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=TicketStatus.OPEN.value, index=True
    )
    subject: Mapped[str] = mapped_column(String(100), default="Compra de Robux")
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "order_id": self.order_id,
            "status": self.status,
            "subject": self.subject,
            "messages_count": self.messages_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "closed_by": self.closed_by,
        }


class Coupon(Base):
    """Modelo de cupom de desconto."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    discount_percent: Mapped[float] = mapped_column(Float, nullable=False)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, default=0)
    min_robux: Mapped[int] = mapped_column(Integer, default=0)
    max_robux: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "discount_percent": self.discount_percent,
            "max_uses": self.max_uses,
            "current_uses": self.current_uses,
            "min_robux": self.min_robux,
            "max_robux": self.max_robux,
            "active": self.active,
            "valid_until": self.valid_until,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }


class Transaction(Base):
    """Modelo de transação financeira."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.PIX.value
    )
    payer_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "status": self.status,
            "payment_method": self.payment_method,
            "payer_email": self.payer_email,
            "payer_name": self.payer_name,
            "raw_data": self.raw_data,
            "created_at": self.created_at,
        }


class Log(Base):
    """Modelo de log."""

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    level: Mapped[str] = mapped_column(String(20), default="info")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "details": self.details,
            "level": self.level,
            "created_at": self.created_at,
        }


class Gamepass(Base):
    """Modelo de gamepass criado."""

    __tablename__ = "gamepasses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gamepass_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    universe_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "gamepass_id": self.gamepass_id,
            "universe_id": self.universe_id,
            "name": self.name,
            "price": self.price,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "is_used": self.is_used,
            "created_at": self.created_at,
            "used_at": self.used_at,
        }


# Modelos Pydantic para validação de entrada (opcional, para compatibilidade)


class UserCreate(PydanticBaseModel):
    discord_id: int
    discord_name: str
    roblox_username: Optional[str] = None
    roblox_id: Optional[int] = None


class OrderCreate(PydanticBaseModel):
    user_id: int
    roblox_username: str
    roblox_id: int
    robux_amount: int
    price_brl: float
    gamepass_price: int
    coupon_code: Optional[str] = None
    discount_percent: float = 0.0
    ticket_channel_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class TicketCreate(PydanticBaseModel):
    user_id: int
    channel_id: int
    subject: str = "Compra de Robux"


class CouponCreate(PydanticBaseModel):
    code: str
    discount_percent: float
    max_uses: Optional[int] = None
    min_robux: int = 0
    max_robux: Optional[int] = None
    valid_until: Optional[datetime] = None
    created_by: int
