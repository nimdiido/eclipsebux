from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update, desc
from .connection import db
from .models import (
    User,
    Order,
    Ticket,
    Coupon,
    Transaction,
    Log,
    Gamepass,
    OrderStatus,
    TicketStatus,
)
from loguru import logger


class UserRepository:
    """Repositório de operações com usuários."""

    @staticmethod
    async def get_or_create(discord_id: int, discord_name: str) -> Dict[str, Any]:
        """Busca ou cria um usuário."""
        async with db.get_session() as session:
            # Busca usuário existente
            result = await session.execute(
                select(User).where(User.discord_id == discord_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                # Cria novo usuário
                user = User(discord_id=discord_id, discord_name=discord_name)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"👤 Novo usuário criado: {discord_name} ({discord_id})")

            return user.to_dict()

    @staticmethod
    async def update(discord_id: int, **kwargs) -> bool:
        """Atualiza dados do usuário."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        async with db.get_session() as session:
            result = await session.execute(
                update(User).where(User.discord_id == discord_id).values(**kwargs)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def increment_stats(discord_id: int, spent: float, robux: int) -> None:
        """Incrementa estatísticas do usuário."""
        async with db.get_session() as session:
            result = await session.execute(
                select(User).where(User.discord_id == discord_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.total_spent += spent
                user.total_robux_bought += robux
                user.orders_count += 1
                user.updated_at = datetime.now(timezone.utc)
                await session.commit()

    @staticmethod
    async def get_by_id(discord_id: int) -> Optional[Dict[str, Any]]:
        """Busca usuário por ID."""
        async with db.get_session() as session:
            result = await session.execute(
                select(User).where(User.discord_id == discord_id)
            )
            user = result.scalar_one_or_none()
            return user.to_dict() if user else None

    @staticmethod
    async def get_top_buyers(limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna os maiores compradores."""
        async with db.get_session() as session:
            result = await session.execute(
                select(User)
                .where(User.total_spent > 0)
                .order_by(desc(User.total_spent))
                .limit(limit)
            )
            users = result.scalars().all()
            return [u.to_dict() for u in users]


class OrderRepository:
    """Repositório de operações com pedidos."""

    @staticmethod
    async def create(order_data) -> str:
        """Cria um novo pedido."""
        async with db.get_session() as session:
            # Suporta tanto objeto Order quanto dict/Pydantic model
            if hasattr(order_data, "to_dict"):
                order = order_data
            else:
                order = Order(
                    order_id=getattr(order_data, "order_id", None),
                    user_id=(
                        order_data.user_id
                        if hasattr(order_data, "user_id")
                        else order_data["user_id"]
                    ),
                    roblox_username=(
                        order_data.roblox_username
                        if hasattr(order_data, "roblox_username")
                        else order_data["roblox_username"]
                    ),
                    roblox_id=(
                        order_data.roblox_id
                        if hasattr(order_data, "roblox_id")
                        else order_data["roblox_id"]
                    ),
                    robux_amount=(
                        order_data.robux_amount
                        if hasattr(order_data, "robux_amount")
                        else order_data["robux_amount"]
                    ),
                    price_brl=(
                        order_data.price_brl
                        if hasattr(order_data, "price_brl")
                        else order_data["price_brl"]
                    ),
                    gamepass_price=(
                        order_data.gamepass_price
                        if hasattr(order_data, "gamepass_price")
                        else order_data["gamepass_price"]
                    ),
                    coupon_code=getattr(order_data, "coupon_code", None),
                    discount_percent=getattr(order_data, "discount_percent", 0.0),
                    ticket_channel_id=getattr(order_data, "ticket_channel_id", None),
                    expires_at=getattr(order_data, "expires_at", None),
                )
            session.add(order)
            await session.commit()
            await session.refresh(order)
            logger.info(f"📦 Pedido criado: {order.order_id}")
            return order.order_id

    @staticmethod
    async def get_by_id(order_id: str) -> Optional[Dict[str, Any]]:
        """Busca pedido por ID."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            return order.to_dict() if order else None

    @staticmethod
    async def get_by_payment_id(payment_id: str) -> Optional[Dict[str, Any]]:
        """Busca pedido por ID do pagamento."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.payment_id == payment_id)
            )
            order = result.scalar_one_or_none()
            return order.to_dict() if order else None

    @staticmethod
    async def update_status(order_id: str, status: OrderStatus, **kwargs) -> bool:
        """Atualiza status do pedido."""
        update_data = {
            "status": status.value if isinstance(status, OrderStatus) else status,
            "updated_at": datetime.now(timezone.utc),
            **kwargs,
        }

        if status == OrderStatus.PAID:
            update_data["paid_at"] = datetime.now(timezone.utc)
        elif status == OrderStatus.DELIVERED:
            update_data["delivered_at"] = datetime.now(timezone.utc)

        async with db.get_session() as session:
            result = await session.execute(
                update(Order).where(Order.order_id == order_id).values(**update_data)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def update(order_id: str, **kwargs) -> bool:
        """Atualiza dados do pedido."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        async with db.get_session() as session:
            result = await session.execute(
                update(Order).where(Order.order_id == order_id).values(**kwargs)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_user_orders(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca pedidos de um usuário."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(desc(Order.created_at))
                .limit(limit)
            )
            orders = result.scalars().all()
            return [o.to_dict() for o in orders]

    @staticmethod
    async def get_pending_orders() -> List[Dict[str, Any]]:
        """Busca pedidos pendentes."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.status == OrderStatus.PENDING.value)
            )
            orders = result.scalars().all()
            return [o.to_dict() for o in orders]

    @staticmethod
    async def get_expired_orders(minutes: int = 30) -> List[Dict[str, Any]]:
        """Busca pedidos expirados."""
        expiration_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        async with db.get_session() as session:
            result = await session.execute(
                select(Order).where(
                    Order.status == OrderStatus.PENDING.value,
                    Order.created_at < expiration_time,
                )
            )
            orders = result.scalars().all()
            return [o.to_dict() for o in orders]

    @staticmethod
    async def add_note(order_id: str, note: str) -> None:
        """Adiciona nota ao pedido."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Order).where(Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                notes = order.notes or []
                notes.append(f"[{datetime.now().strftime('%d/%m %H:%M')}] {note}")
                order.notes = notes
                order.updated_at = datetime.now(timezone.utc)
                await session.commit()


class TicketRepository:
    """Repositório de operações com tickets."""

    @staticmethod
    async def create(ticket_data) -> str:
        """Cria um novo ticket."""
        async with db.get_session() as session:
            if hasattr(ticket_data, "to_dict"):
                ticket = ticket_data
            else:
                ticket = Ticket(
                    user_id=(
                        ticket_data.user_id
                        if hasattr(ticket_data, "user_id")
                        else ticket_data["user_id"]
                    ),
                    channel_id=(
                        ticket_data.channel_id
                        if hasattr(ticket_data, "channel_id")
                        else ticket_data["channel_id"]
                    ),
                    subject=getattr(ticket_data, "subject", "Compra de Robux"),
                )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            logger.info(f"🎫 Ticket criado: {ticket.ticket_id}")
            return ticket.ticket_id

    @staticmethod
    async def get_by_id(ticket_id: str) -> Optional[Dict[str, Any]]:
        """Busca ticket por ID."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.ticket_id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            return ticket.to_dict() if ticket else None

    @staticmethod
    async def get_by_channel(channel_id: int) -> Optional[Dict[str, Any]]:
        """Busca ticket por canal."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.channel_id == channel_id)
            )
            ticket = result.scalar_one_or_none()
            return ticket.to_dict() if ticket else None

    @staticmethod
    async def get_user_open_ticket(user_id: int) -> Optional[Dict[str, Any]]:
        """Busca ticket aberto do usuário (mais recente)."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Ticket)
                .where(
                    Ticket.user_id == user_id,
                    Ticket.status.in_(
                        [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
                    ),
                )
                .order_by(desc(Ticket.created_at))
                .limit(1)
            )
            ticket = result.scalar_one_or_none()
            return ticket.to_dict() if ticket else None

    @staticmethod
    async def update_status(ticket_id: str, status: TicketStatus, **kwargs) -> bool:
        """Atualiza status do ticket."""
        update_data = {
            "status": status.value if isinstance(status, TicketStatus) else status,
            "updated_at": datetime.now(timezone.utc),
            **kwargs,
        }

        if status == TicketStatus.CLOSED:
            update_data["closed_at"] = datetime.now(timezone.utc)

        async with db.get_session() as session:
            result = await session.execute(
                update(Ticket)
                .where(Ticket.ticket_id == ticket_id)
                .values(**update_data)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def link_order(ticket_id: str, order_id: str) -> bool:
        """Vincula um pedido ao ticket."""
        async with db.get_session() as session:
            result = await session.execute(
                update(Ticket)
                .where(Ticket.ticket_id == ticket_id)
                .values(order_id=order_id, updated_at=datetime.now(timezone.utc))
            )
            await session.commit()
            return result.rowcount > 0


class CouponRepository:
    """Repositório de operações com cupons."""

    @staticmethod
    async def create(coupon_data) -> str:
        """Cria um novo cupom."""
        async with db.get_session() as session:
            if hasattr(coupon_data, "to_dict"):
                coupon = coupon_data
            else:
                coupon = Coupon(
                    code=(
                        coupon_data.code.upper()
                        if hasattr(coupon_data, "code")
                        else coupon_data["code"].upper()
                    ),
                    discount_percent=(
                        coupon_data.discount_percent
                        if hasattr(coupon_data, "discount_percent")
                        else coupon_data["discount_percent"]
                    ),
                    max_uses=getattr(coupon_data, "max_uses", None),
                    min_robux=getattr(coupon_data, "min_robux", 0),
                    max_robux=getattr(coupon_data, "max_robux", None),
                    valid_until=getattr(coupon_data, "valid_until", None),
                    created_by=(
                        coupon_data.created_by
                        if hasattr(coupon_data, "created_by")
                        else coupon_data["created_by"]
                    ),
                )
            session.add(coupon)
            await session.commit()
            await session.refresh(coupon)
            logger.info(f"🎟️ Cupom criado: {coupon.code}")
            return coupon.code

    @staticmethod
    async def get_by_code(code: str) -> Optional[Dict[str, Any]]:
        """Busca cupom por código."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Coupon).where(Coupon.code == code.upper())
            )
            coupon = result.scalar_one_or_none()
            return coupon.to_dict() if coupon else None

    @staticmethod
    async def validate(code: str, robux_amount: int) -> tuple[bool, str, float]:
        """
        Valida um cupom.
        Retorna: (válido, mensagem, desconto)
        """
        coupon = await CouponRepository.get_by_code(code)

        if not coupon:
            return False, "Cupom não encontrado", 0.0

        if not coupon.get("active", False):
            return False, "Cupom inativo", 0.0

        if coupon.get("valid_until") and coupon["valid_until"] < datetime.now(
            timezone.utc
        ):
            return False, "Cupom expirado", 0.0

        if (
            coupon.get("max_uses")
            and coupon.get("current_uses", 0) >= coupon["max_uses"]
        ):
            return False, "Cupom esgotado", 0.0

        if robux_amount < coupon.get("min_robux", 0):
            return False, f"Mínimo de {coupon['min_robux']} Robux", 0.0

        if coupon.get("max_robux") and robux_amount > coupon["max_robux"]:
            return False, f"Máximo de {coupon['max_robux']} Robux", 0.0

        return True, "Cupom válido!", coupon["discount_percent"]

    @staticmethod
    async def use(code: str) -> bool:
        """Incrementa uso do cupom."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Coupon).where(Coupon.code == code.upper())
            )
            coupon = result.scalar_one_or_none()
            if coupon:
                coupon.current_uses += 1
                await session.commit()
                return True
            return False

    @staticmethod
    async def deactivate(code: str) -> bool:
        """Desativa um cupom."""
        async with db.get_session() as session:
            result = await session.execute(
                update(Coupon).where(Coupon.code == code.upper()).values(active=False)
            )
            await session.commit()
            return result.rowcount > 0


class TransactionRepository:
    """Repositório de operações com transações."""

    @staticmethod
    async def create(transaction_data) -> str:
        """Cria uma nova transação."""
        async with db.get_session() as session:
            if hasattr(transaction_data, "to_dict"):
                transaction = transaction_data
            else:
                transaction = Transaction(
                    payment_id=(
                        transaction_data.payment_id
                        if hasattr(transaction_data, "payment_id")
                        else transaction_data["payment_id"]
                    ),
                    order_id=(
                        transaction_data.order_id
                        if hasattr(transaction_data, "order_id")
                        else transaction_data["order_id"]
                    ),
                    user_id=(
                        transaction_data.user_id
                        if hasattr(transaction_data, "user_id")
                        else transaction_data["user_id"]
                    ),
                    amount=(
                        transaction_data.amount
                        if hasattr(transaction_data, "amount")
                        else transaction_data["amount"]
                    ),
                    status=(
                        transaction_data.status
                        if hasattr(transaction_data, "status")
                        else transaction_data["status"]
                    ),
                )
            session.add(transaction)
            await session.commit()
            await session.refresh(transaction)
            return transaction.payment_id

    @staticmethod
    async def get_by_payment_id(payment_id: str) -> Optional[Dict[str, Any]]:
        """Busca transação por ID do pagamento."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.payment_id == payment_id)
            )
            transaction = result.scalar_one_or_none()
            return transaction.to_dict() if transaction else None


class LogRepository:
    """Repositório de operações com logs."""

    @staticmethod
    async def create(log_data) -> None:
        """Cria um novo log."""
        async with db.get_session() as session:
            if hasattr(log_data, "to_dict"):
                log = log_data
            else:
                log = Log(
                    action=(
                        log_data.action
                        if hasattr(log_data, "action")
                        else log_data["action"]
                    ),
                    user_id=getattr(log_data, "user_id", None),
                    order_id=getattr(log_data, "order_id", None),
                    details=getattr(log_data, "details", {}),
                    level=getattr(log_data, "level", "info"),
                )
            session.add(log)
            await session.commit()

    @staticmethod
    async def log(
        action: str,
        user_id: int = None,
        order_id: str = None,
        details: Dict = None,
        level: str = "info",
    ) -> None:
        """Helper para criar log rapidamente."""
        log = Log(
            action=action,
            user_id=user_id,
            order_id=order_id,
            details=details or {},
            level=level,
        )
        async with db.get_session() as session:
            session.add(log)
            await session.commit()

    @staticmethod
    async def get_recent(limit: int = 50) -> List[Dict[str, Any]]:
        """Busca logs recentes."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Log).order_by(desc(Log.created_at)).limit(limit)
            )
            logs = result.scalars().all()
            return [log_item.to_dict() for log_item in logs]


class GamepassRepository:
    """Repositório de operações com gamepasses."""

    @staticmethod
    async def create(gamepass_data) -> int:
        """Registra um gamepass criado."""
        async with db.get_session() as session:
            if hasattr(gamepass_data, "to_dict"):
                gamepass = gamepass_data
            else:
                gamepass = Gamepass(
                    gamepass_id=(
                        gamepass_data.gamepass_id
                        if hasattr(gamepass_data, "gamepass_id")
                        else gamepass_data["gamepass_id"]
                    ),
                    universe_id=(
                        gamepass_data.universe_id
                        if hasattr(gamepass_data, "universe_id")
                        else gamepass_data["universe_id"]
                    ),
                    name=(
                        gamepass_data.name
                        if hasattr(gamepass_data, "name")
                        else gamepass_data["name"]
                    ),
                    price=(
                        gamepass_data.price
                        if hasattr(gamepass_data, "price")
                        else gamepass_data["price"]
                    ),
                    order_id=(
                        gamepass_data.order_id
                        if hasattr(gamepass_data, "order_id")
                        else gamepass_data["order_id"]
                    ),
                    user_id=(
                        gamepass_data.user_id
                        if hasattr(gamepass_data, "user_id")
                        else gamepass_data["user_id"]
                    ),
                )
            session.add(gamepass)
            await session.commit()
            await session.refresh(gamepass)
            return gamepass.gamepass_id

    @staticmethod
    async def get_by_id(gamepass_id: int) -> Optional[Dict[str, Any]]:
        """Busca gamepass por ID."""
        async with db.get_session() as session:
            result = await session.execute(
                select(Gamepass).where(Gamepass.gamepass_id == gamepass_id)
            )
            gamepass = result.scalar_one_or_none()
            return gamepass.to_dict() if gamepass else None

    @staticmethod
    async def mark_used(gamepass_id: int) -> bool:
        """Marca gamepass como usado."""
        async with db.get_session() as session:
            result = await session.execute(
                update(Gamepass)
                .where(Gamepass.gamepass_id == gamepass_id)
                .values(is_used=True, used_at=datetime.now(timezone.utc))
            )
            await session.commit()
            return result.rowcount > 0
