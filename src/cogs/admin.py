import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from src.config import get_settings
from src.database import (
    OrderRepository,
    OrderStatus,
    UserRepository,
    CouponRepository,
    CouponCreate,
    LogRepository,
)


class AdminCog(commands.Cog):
    """Comandos administrativos."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_admin():
        """Decorator para verificar se é admin."""

        async def predicate(interaction: discord.Interaction) -> bool:
            settings = get_settings()
            return any(r.id == settings.role_admin_id for r in interaction.user.roles)

        return app_commands.check(predicate)

    # ==================== CUPONS ====================

    @app_commands.command(
        name="cupom_criar", description="Cria um novo cupom de desconto"
    )
    @app_commands.describe(
        codigo="Código do cupom",
        desconto="Desconto em porcentagem (ex: 10 para 10%)",
        max_usos="Máximo de usos (opcional)",
        min_robux="Mínimo de Robux para usar (opcional)",
    )
    @is_admin()
    async def create_coupon(
        self,
        interaction: discord.Interaction,
        codigo: str,
        desconto: int,
        max_usos: Optional[int] = None,
        min_robux: Optional[int] = 0,
    ):
        """Cria um novo cupom."""
        if desconto <= 0 or desconto > 100:
            await interaction.response.send_message(
                "❌ Desconto deve ser entre 1 e 100%", ephemeral=True
            )
            return

        # Verifica se já existe
        existing = await CouponRepository.get_by_code(codigo)
        if existing:
            await interaction.response.send_message(
                f"❌ Cupom `{codigo}` já existe!", ephemeral=True
            )
            return

        coupon = CouponCreate(
            code=codigo.upper(),
            discount_percent=desconto / 100,
            max_uses=max_usos,
            min_robux=min_robux or 0,
            created_by=interaction.user.id,
        )

        await CouponRepository.create(coupon)

        embed = discord.Embed(title="✅ Cupom Criado!", color=discord.Color.green())
        embed.add_field(name="Código", value=f"`{codigo.upper()}`", inline=True)
        embed.add_field(name="Desconto", value=f"{desconto}%", inline=True)
        embed.add_field(
            name="Usos Máximos", value=str(max_usos or "Ilimitado"), inline=True
        )
        embed.add_field(name="Mínimo Robux", value=str(min_robux or 0), inline=True)

        await interaction.response.send_message(embed=embed)

        await LogRepository.log(
            action="coupon_created",
            user_id=interaction.user.id,
            details={"code": codigo.upper(), "discount": desconto},
        )

    @app_commands.command(name="cupom_desativar", description="Desativa um cupom")
    @app_commands.describe(codigo="Código do cupom")
    @is_admin()
    async def deactivate_coupon(self, interaction: discord.Interaction, codigo: str):
        """Desativa um cupom."""
        success = await CouponRepository.deactivate(codigo)

        if success:
            await interaction.response.send_message(
                f"✅ Cupom `{codigo.upper()}` desativado!"
            )
        else:
            await interaction.response.send_message(
                f"❌ Cupom `{codigo}` não encontrado.", ephemeral=True
            )

    # ==================== PEDIDOS ====================

    @app_commands.command(
        name="pedido", description="Consulta informações de um pedido"
    )
    @app_commands.describe(pedido_id="ID do pedido")
    @is_admin()
    async def check_order(self, interaction: discord.Interaction, pedido_id: str):
        """Consulta um pedido."""
        order = await OrderRepository.get_by_id(pedido_id.upper())

        if not order:
            await interaction.response.send_message(
                f"❌ Pedido `{pedido_id}` não encontrado.", ephemeral=True
            )
            return

        status_emoji = {
            "pending": "⏳",
            "paid": "💰",
            "processing": "🔄",
            "delivered": "✅",
            "cancelled": "❌",
            "refunded": "💸",
            "expired": "⏰",
        }

        embed = discord.Embed(
            title=f"📦 Pedido {order['order_id']}",
            color=discord.Color.blue(),
            timestamp=order.get("created_at"),
        )

        status = order.get("status", "unknown")

        embed.add_field(
            name="Status",
            value=f"{status_emoji.get(status, '❓')} {status.upper()}",
            inline=True,
        )
        embed.add_field(name="Usuário", value=f"<@{order['user_id']}>", inline=True)
        embed.add_field(
            name="Roblox", value=f"`{order['roblox_username']}`", inline=True
        )
        embed.add_field(name="Robux", value=f"{order['robux_amount']:,}", inline=True)
        embed.add_field(name="Valor", value=f"R$ {order['price_brl']:.2f}", inline=True)

        if order.get("coupon_code"):
            embed.add_field(
                name="Cupom", value=f"`{order['coupon_code']}`", inline=True
            )

        if order.get("payment_id"):
            embed.add_field(
                name="Payment ID", value=f"`{order['payment_id']}`", inline=True
            )

        if order.get("paid_at"):
            embed.add_field(
                name="Pago em",
                value=order["paid_at"].strftime("%d/%m/%Y %H:%M"),
                inline=True,
            )

        if order.get("delivered_at"):
            embed.add_field(
                name="Entregue em",
                value=order["delivered_at"].strftime("%d/%m/%Y %H:%M"),
                inline=True,
            )

        if order.get("notes"):
            notes = "\n".join(order["notes"][-5:])
            embed.add_field(name="Notas", value=notes, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="entregar", description="Marca um pedido como entregue manualmente"
    )
    @app_commands.describe(pedido_id="ID do pedido")
    @is_admin()
    async def deliver_order(self, interaction: discord.Interaction, pedido_id: str):
        """Entrega manual de pedido."""
        order = await OrderRepository.get_by_id(pedido_id.upper())

        if not order:
            await interaction.response.send_message(
                "❌ Pedido não encontrado.", ephemeral=True
            )
            return

        if order["status"] not in [
            OrderStatus.PAID.value,
            OrderStatus.PROCESSING.value,
        ]:
            await interaction.response.send_message(
                f"❌ Pedido não está pago. Status: {order['status']}", ephemeral=True
            )
            return

        await OrderRepository.update_status(pedido_id.upper(), OrderStatus.DELIVERED)
        await OrderRepository.add_note(
            pedido_id.upper(), f"Entregue manualmente por {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ Pedido `{pedido_id.upper()}` marcado como entregue!"
        )

        await LogRepository.log(
            action="manual_delivery",
            user_id=interaction.user.id,
            order_id=pedido_id.upper(),
            level="warning",
        )

    @app_commands.command(name="reembolsar", description="Reembolsa um pedido")
    @app_commands.describe(pedido_id="ID do pedido")
    @is_admin()
    async def refund_order(self, interaction: discord.Interaction, pedido_id: str):
        """Reembolsa um pedido."""
        from src.services import mercadopago_service

        order = await OrderRepository.get_by_id(pedido_id.upper())

        if not order:
            await interaction.response.send_message(
                "❌ Pedido não encontrado.", ephemeral=True
            )
            return

        if order["status"] not in [OrderStatus.PAID.value, OrderStatus.DELIVERED.value]:
            await interaction.response.send_message(
                f"❌ Não é possível reembolsar. Status: {order['status']}",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Tenta reembolsar via Mercado Pago
        success, data = await mercadopago_service.refund_payment(order["payment_id"])

        if success:
            await OrderRepository.update_status(pedido_id.upper(), OrderStatus.REFUNDED)
            await OrderRepository.add_note(
                pedido_id.upper(), f"Reembolsado por {interaction.user}"
            )

            embed = discord.Embed(
                title="💸 Pedido Reembolsado",
                description=f"Pedido `{pedido_id.upper()}` foi reembolsado com sucesso!",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)

            await LogRepository.log(
                action="refund",
                user_id=interaction.user.id,
                order_id=pedido_id.upper(),
                details={"amount": order["price_brl"]},
                level="warning",
            )
        else:
            await interaction.followup.send(f"❌ Erro ao reembolsar: {data}")

    # ==================== ESTATÍSTICAS ====================

    @app_commands.command(name="stats", description="Mostra estatísticas do bot")
    @is_admin()
    async def show_stats(self, interaction: discord.Interaction):
        """Mostra estatísticas."""
        from src.database.connection import db
        from sqlalchemy import select, func
        from src.database.models import Order, User

        async with db.get_session() as session:
            # Conta pedidos por status
            total_orders = await session.scalar(select(func.count(Order.id)))
            delivered = await session.scalar(
                select(func.count(Order.id)).where(
                    Order.status == OrderStatus.DELIVERED.value
                )
            )
            pending = await session.scalar(
                select(func.count(Order.id)).where(
                    Order.status == OrderStatus.PENDING.value
                )
            )
            cancelled = await session.scalar(
                select(func.count(Order.id)).where(
                    Order.status == OrderStatus.CANCELLED.value
                )
            )

            # Total vendido
            revenue_result = await session.execute(
                select(
                    func.sum(Order.price_brl).label("total"),
                    func.sum(Order.robux_amount).label("robux"),
                ).where(Order.status == OrderStatus.DELIVERED.value)
            )
            row = revenue_result.first()
            total_revenue = row.total or 0 if row else 0
            total_robux = row.robux or 0 if row else 0

            # Usuários
            total_users = await session.scalar(select(func.count(User.id)))

        embed = discord.Embed(
            title="📊 Estatísticas",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )

        embed.add_field(
            name="📦 Total de Pedidos", value=str(total_orders or 0), inline=True
        )
        embed.add_field(name="✅ Entregues", value=str(delivered or 0), inline=True)
        embed.add_field(name="⏳ Pendentes", value=str(pending or 0), inline=True)
        embed.add_field(name="❌ Cancelados", value=str(cancelled or 0), inline=True)
        embed.add_field(
            name="💰 Faturamento", value=f"R$ {total_revenue:,.2f}", inline=True
        )
        embed.add_field(name="💎 Robux Vendidos", value=f"{total_robux:,}", inline=True)
        embed.add_field(name="👥 Usuários", value=str(total_users or 0), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="top_compradores", description="Lista os maiores compradores"
    )
    @is_admin()
    async def top_buyers(self, interaction: discord.Interaction):
        """Lista top compradores."""
        buyers = await UserRepository.get_top_buyers(10)

        if not buyers:
            await interaction.response.send_message(
                "❌ Nenhum comprador ainda.", ephemeral=True
            )
            return

        embed = discord.Embed(title="🏆 Top Compradores", color=discord.Color.gold())

        description = ""
        medals = ["🥇", "🥈", "🥉"]

        for i, buyer in enumerate(buyers):
            medal = medals[i] if i < 3 else f"{i+1}."
            description += (
                f"{medal} <@{buyer['discord_id']}>\n"
                f"   💰 R$ {buyer['total_spent']:,.2f} • 💎 {buyer['total_robux_bought']:,} Robux\n\n"
            )

        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== UTILITÁRIOS ====================

    @app_commands.command(
        name="anunciar", description="Envia um anúncio no canal de vendas"
    )
    @app_commands.describe(mensagem="Mensagem do anúncio")
    @is_admin()
    async def announce(self, interaction: discord.Interaction, mensagem: str):
        """Envia anúncio."""
        settings = get_settings()
        channel = self.bot.get_channel(settings.channel_vendas_id)

        if not channel:
            await interaction.response.send_message(
                "❌ Canal de vendas não encontrado.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📢 Anúncio",
            description=mensagem,
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Por {interaction.user}")

        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Anúncio enviado!", ephemeral=True)

    @app_commands.command(
        name="setup_painel", description="Configura o painel de vendas"
    )
    @is_admin()
    async def setup_panel(self, interaction: discord.Interaction):
        """Configura painel de vendas."""
        from src.cogs.tickets import setup_ticket_panel

        await interaction.response.defer(ephemeral=True)
        await setup_ticket_panel(self.bot)
        await interaction.followup.send("✅ Painel configurado!")

    @app_commands.command(
        name="saldo_robux", description="Verifica saldo de Robux da conta do bot"
    )
    @is_admin()
    async def check_robux_balance(self, interaction: discord.Interaction):
        """Verifica saldo de Robux do bot."""
        from src.services import roblox_api

        await interaction.response.defer(ephemeral=True)

        balance = await roblox_api.get_my_robux_balance()
        user = await roblox_api.get_authenticated_user()

        if balance is not None and user:
            embed = discord.Embed(
                title="💎 Saldo de Robux",
                color=discord.Color.green(),
            )
            embed.add_field(name="Conta", value=f"`{user.get('name')}`", inline=True)
            embed.add_field(name="ID", value=f"`{user.get('id')}`", inline=True)
            embed.add_field(name="Saldo", value=f"**{balance:,} R$**", inline=True)

            # Alerta se saldo baixo
            if balance < 1000:
                embed.add_field(
                    name="⚠️ Atenção",
                    value="Saldo baixo! Adicione mais Robux para continuar vendendo.",
                    inline=False,
                )
                embed.color = discord.Color.orange()
        else:
            embed = discord.Embed(
                title="❌ Erro",
                description="Não foi possível verificar o saldo. Cookie pode estar inválido.",
                color=discord.Color.red(),
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="forcar_compra", description="Força a compra de um gamepass manualmente"
    )
    @app_commands.describe(pedido_id="ID do pedido", gamepass_id="ID do gamepass")
    @is_admin()
    async def force_purchase(
        self, interaction: discord.Interaction, pedido_id: str, gamepass_id: int
    ):
        """Força compra manual de gamepass."""
        from src.services import roblox_api

        order = await OrderRepository.get_by_id(pedido_id.upper())

        if not order:
            await interaction.response.send_message(
                "❌ Pedido não encontrado.", ephemeral=True
            )
            return

        if order["status"] not in [
            OrderStatus.PAID.value,
            OrderStatus.PROCESSING.value,
        ]:
            await interaction.response.send_message(
                f"❌ Pedido não está pago. Status: {order['status']}", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Tenta comprar
        success, message = await roblox_api.full_purchase_flow(
            gamepass_id=gamepass_id,
            expected_price=order["gamepass_price"],
            expected_owner_id=order["roblox_id"],
        )

        if success:
            await OrderRepository.update_status(
                pedido_id.upper(), OrderStatus.DELIVERED
            )
            await OrderRepository.update(pedido_id.upper(), gamepass_id=gamepass_id)

            embed = discord.Embed(
                title="✅ Compra Forçada",
                description=(
                    f"**Pedido:** `{pedido_id.upper()}`\n"
                    f"**Gamepass:** `{gamepass_id}`\n"
                    f"**Preço:** {order['gamepass_price']:,} R$\n\n"
                    "Gamepass comprado com sucesso!"
                ),
                color=discord.Color.green(),
            )

            await LogRepository.log(
                action="forced_purchase",
                user_id=interaction.user.id,
                order_id=pedido_id.upper(),
                details={"gamepass_id": gamepass_id},
                level="warning",
            )
        else:
            embed = discord.Embed(
                title="❌ Falha na Compra",
                description=message,
                color=discord.Color.red(),
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
