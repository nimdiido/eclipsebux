import discord
from discord import ui
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import asyncio
import base64
import io
import re
from loguru import logger

from src.config import get_settings
from src.database import (
    OrderRepository,
    OrderCreate,
    OrderStatus,
    UserRepository,
    CouponRepository,
    TicketRepository,
    Transaction,
    TransactionRepository,
    LogRepository,
)
from src.services import mercadopago_service, roblox_api


class OrdersCog(commands.Cog):
    """Cog de gerenciamento de pedidos."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending_confirmations = {}  # order_id -> asyncio.Task

    async def process_order(
        self,
        interaction: discord.Interaction,
        ticket_id: str,
        robux_amount: int,
        roblox_username: str,
    ) -> None:
        """Processa um novo pedido."""
        settings = get_settings()

        # Valida usuário Roblox
        valid, roblox_id, message = await roblox_api.validate_username(roblox_username)

        if not valid:
            embed = discord.Embed(
                title="❌ Usuário Inválido",
                description=f"O usuário **{roblox_username}** não foi encontrado no Roblox.\n\n{message}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return

        # Calcula preço
        base_price = settings.calculate_price(robux_amount)

        # Verifica cupom
        coupon_code = None
        discount_percent = 0.0

        ticket_coupons = getattr(self.bot, "ticket_coupons", {})
        if ticket_id in ticket_coupons:
            coupon_data = ticket_coupons[ticket_id]
            coupon_code = coupon_data["code"]
            discount_percent = coupon_data["discount"]

        # Aplica desconto
        discount_value = base_price * discount_percent
        final_price = base_price - discount_value

        # Preço do gamepass
        gamepass_price = settings.calculate_gamepass_price(robux_amount)

        # Cria usuário se não existir
        await UserRepository.get_or_create(interaction.user.id, str(interaction.user))

        # Cria pedido
        order = OrderCreate(
            user_id=interaction.user.id,
            roblox_username=roblox_username,
            roblox_id=roblox_id,
            robux_amount=robux_amount,
            price_brl=final_price,
            gamepass_price=gamepass_price,
            coupon_code=coupon_code,
            discount_percent=discount_percent,
            ticket_channel_id=interaction.channel.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.pix_expiration_minutes),
        )

        order_id = await OrderRepository.create(order)
        order_dict = await OrderRepository.get_by_id(order_id)

        # Vincula ao ticket
        await TicketRepository.link_order(ticket_id, order_id)

        # Cria pagamento PIX
        success, pix_data = await mercadopago_service.create_pix_payment(
            amount=final_price,
            order_id=order_id,
            description=f"Compra de {robux_amount} Robux",
            payer_email=f"user{interaction.user.id}@discord.com",
            payer_name=str(interaction.user),
        )

        if not success:
            embed = discord.Embed(
                title="❌ Erro ao Gerar PIX",
                description="Ocorreu um erro ao gerar o pagamento. Tente novamente.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            await OrderRepository.update_status(order_id, OrderStatus.CANCELLED)
            return

        # Atualiza pedido com dados do PIX
        await OrderRepository.update(
            order_id,
            payment_id=pix_data["payment_id"],
            pix_code=pix_data["pix_code"],
            pix_qrcode=pix_data.get("pix_qrcode_base64", ""),
        )

        # Remove cupom do cache
        if ticket_id in ticket_coupons:
            del ticket_coupons[ticket_id]

        # Envia detalhes do pedido
        await self._send_order_details(interaction.channel, order_dict, pix_data)

        # Inicia monitoramento do pagamento
        await self._start_payment_monitoring(order_id)

        # Log
        await LogRepository.log(
            action="order_created",
            user_id=interaction.user.id,
            order_id=order_id,
            details={
                "robux": robux_amount,
                "price": final_price,
                "roblox_user": roblox_username,
                "coupon": coupon_code,
            },
        )

    async def _send_order_details(
        self, channel: discord.TextChannel, order: dict, pix_data: dict
    ) -> None:
        """Envia detalhes do pedido com QR Code - Design profissional."""
        settings = get_settings()

        # ═══════════════════════════════════════════════════════════
        # EMBED 1: Resumo do Pedido
        # ═══════════════════════════════════════════════════════════
        order_embed = discord.Embed(
            title="🧾 Resumo do Pedido",
            color=0x5865F2,  # Blurple
        )

        # Linha separadora visual
        order_embed.description = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        order_embed.add_field(
            name="🔢 Pedido",
            value=f"```{order['order_id']}```",
            inline=True,
        )
        order_embed.add_field(
            name="👤 Roblox",
            value=f"```{order['roblox_username']}```",
            inline=True,
        )
        order_embed.add_field(
            name="\u200b",  # Campo vazio para alinhamento
            value="\u200b",
            inline=True,
        )

        order_embed.add_field(
            name="💎 Quantidade",
            value=f"**{order['robux_amount']:,}** Robux",
            inline=True,
        )

        # Mostra desconto se houver
        if order.get("discount_percent", 0) > 0:
            original_price = order["price_brl"] / (1 - order["discount_percent"])
            order_embed.add_field(
                name="🏷️ Desconto",
                value=f"~~R$ {original_price:.2f}~~ → **R$ {order['price_brl']:.2f}**\n`{order['coupon_code']}` (-{order['discount_percent']*100:.0f}%)",
                inline=True,
            )
        else:
            order_embed.add_field(
                name="💵 Valor",
                value=f"**R$ {order['price_brl']:.2f}**",
                inline=True,
            )

        order_embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True,
        )

        # ═══════════════════════════════════════════════════════════
        # EMBED 2: QR Code PIX (com imagem)
        # ═══════════════════════════════════════════════════════════
        pix_qr_embed = discord.Embed(
            title="<:pix:1234567890> Pagamento PIX",
            description=(
                "Escaneie o QR Code abaixo com seu app de banco\n"
                "ou use o código Copia e Cola."
            ),
            color=0x00D166,  # Verde PIX
        )
        pix_qr_embed.set_image(url="attachment://qrcode.png")

        # Cria arquivo do QR Code
        files = []
        if pix_data.get("pix_qrcode_base64"):
            try:
                qr_bytes = base64.b64decode(pix_data["pix_qrcode_base64"])
                files.append(discord.File(io.BytesIO(qr_bytes), filename="qrcode.png"))
            except Exception:
                pass

        # ═══════════════════════════════════════════════════════════
        # EMBED 3: Código Copia e Cola
        # ═══════════════════════════════════════════════════════════
        pix_code = pix_data["pix_code"]

        # Trunca o código se muito longo para exibição bonita
        if len(pix_code) > 300:
            display_code = pix_code[:150] + "..." + pix_code[-50:]
        else:
            display_code = pix_code

        pix_copy_embed = discord.Embed(
            title="📋 Copia e Cola",
            description=f"```{display_code}```",
            color=0x00D166,
        )
        pix_copy_embed.add_field(
            name="💡 Dica",
            value="Clique no botão abaixo para copiar o código completo!",
            inline=False,
        )

        # ═══════════════════════════════════════════════════════════
        # EMBED 4: Instruções e Timer
        # ═══════════════════════════════════════════════════════════
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.pix_expiration_minutes
        )
        expires_timestamp = int(expires_at.timestamp())

        timer_embed = discord.Embed(
            title="⏰ Tempo Limite",
            description=(
                f"Este pagamento expira <t:{expires_timestamp}:R>\n\n"
                "**Após o pagamento:**\n"
                "✅ Confirmação automática em segundos\n"
                "📝 Você receberá instruções para criar o Gamepass\n"
                "💎 Robux entregues instantaneamente!"
            ),
            color=0xFEE75C,  # Amarelo
        )
        timer_embed.set_footer(
            text="⚠️ Não feche este ticket até concluir a compra",
        )

        # View com botões
        view = OrderActionsView()

        await channel.send(
            embeds=[order_embed, pix_qr_embed, pix_copy_embed, timer_embed],
            files=files,
            view=view,
        )

    async def _start_payment_monitoring(self, order_id: str) -> None:
        """Inicia monitoramento de pagamento em background."""

        async def monitor():
            settings = get_settings()
            start_time = datetime.now(timezone.utc)
            timeout = timedelta(minutes=settings.pix_expiration_minutes)

            while datetime.now(timezone.utc) - start_time < timeout:
                order = await OrderRepository.get_by_id(order_id)

                if not order or order["status"] != OrderStatus.PENDING.value:
                    return

                # Verifica status do pagamento
                status, data = await mercadopago_service.check_payment_status(
                    order["payment_id"]
                )

                if status == "approved":
                    await self._handle_payment_confirmed(order_id)
                    return
                elif status in ["cancelled", "rejected"]:
                    await OrderRepository.update_status(order_id, OrderStatus.CANCELLED)
                    return

                await asyncio.sleep(10)

            # Timeout - expira o pedido
            order = await OrderRepository.get_by_id(order_id)
            if order and order["status"] == OrderStatus.PENDING.value:
                await OrderRepository.update_status(order_id, OrderStatus.EXPIRED)

                # Notifica no canal
                channel = self.bot.get_channel(order["ticket_channel_id"])
                if channel:
                    embed = discord.Embed(
                        title="⏰ Pedido Expirado",
                        description=f"O pedido `{order_id}` expirou por falta de pagamento.",
                        color=discord.Color.orange(),
                    )
                    await channel.send(embed=embed)

        # Inicia task
        task = asyncio.create_task(monitor())
        self._pending_confirmations[order_id] = task

    async def _handle_payment_confirmed(self, order_id: str) -> None:
        """Processa pagamento confirmado."""
        order = await OrderRepository.get_by_id(order_id)

        if not order:
            return

        # Atualiza status
        await OrderRepository.update_status(order_id, OrderStatus.PAID)

        # Notifica no canal do ticket
        channel = self.bot.get_channel(order["ticket_channel_id"])

        if channel:
            # ═══════════════════════════════════════════════════════════
            # EMBED 1: Sucesso do Pagamento (com animação visual)
            # ═══════════════════════════════════════════════════════════
            success_embed = discord.Embed(
                title="✅ Pagamento Confirmado com Sucesso!",
                description=(
                    "```diff\n"
                    "+ PAGAMENTO RECEBIDO\n"
                    "```\n"
                    f"**Pedido:** `{order_id}`\n"
                    f"**Valor:** R$ {order['price_brl']:.2f}\n"
                    f"**Robux:** {order['robux_amount']:,}"
                ),
                color=0x00D166,  # Verde
            )
            success_embed.set_thumbnail(
                url="https://i.imgur.com/vXHgGBN.gif"
            )  # Check animado

            # ═══════════════════════════════════════════════════════════
            # EMBED 2: Próximo Passo - Destaque
            # ═══════════════════════════════════════════════════════════
            next_step_embed = discord.Embed(
                title="🎮 Próximo Passo: Criar um Gamepass",
                color=0x5865F2,  # Blurple
            )
            next_step_embed.description = (
                "Para receber seus Robux, você precisa criar um Gamepass\n"
                "em qualquer experiência sua no Roblox.\n\n"
                "**Nós iremos COMPRAR seu gamepass**, e assim os Robux\n"
                "serão transferidos diretamente para sua conta!"
            )

            # ═══════════════════════════════════════════════════════════
            # EMBED 3: Preço do Gamepass (DESTAQUE IMPORTANTE)
            # ═══════════════════════════════════════════════════════════
            price_embed = discord.Embed(
                title="💎 Preço do Gamepass",
                color=0xEB459E,  # Rosa/Magenta para destaque
            )
            price_embed.description = (
                f"# {order['gamepass_price']:,} Robux\n\n"
                f"*Após a taxa de 30% do Roblox, você receberá **{order['robux_amount']:,}** Robux*"
            )
            price_embed.set_footer(text="⚠️ O preço DEVE ser EXATAMENTE este valor!")

            # ═══════════════════════════════════════════════════════════
            # EMBED 4: Instruções Passo a Passo
            # ═══════════════════════════════════════════════════════════
            instructions_embed = discord.Embed(
                title="📋 Como Criar o Gamepass",
                color=0x5865F2,
            )

            instructions_embed.add_field(
                name="Passo 1️⃣",
                value=(
                    "Acesse [Roblox Create](https://create.roblox.com)\n"
                    "e entre em qualquer experiência sua"
                ),
                inline=False,
            )
            instructions_embed.add_field(
                name="Passo 2️⃣",
                value=(
                    "Vá em **Monetization** → **Passes**\n"
                    "e clique em **Create a Pass**"
                ),
                inline=False,
            )
            instructions_embed.add_field(
                name="Passo 3️⃣",
                value=(
                    f"Configure o preço para **{order['gamepass_price']:,} Robux**\n"
                    "e publique o Gamepass"
                ),
                inline=False,
            )
            instructions_embed.add_field(
                name="Passo 4️⃣",
                value=(
                    "Copie o link do Gamepass e clique no botão\n"
                    "**'🎮 Enviar Link do Gamepass'** abaixo"
                ),
                inline=False,
            )

            # ═══════════════════════════════════════════════════════════
            # EMBED 5: Requisitos Importantes
            # ═══════════════════════════════════════════════════════════
            requirements_embed = discord.Embed(
                title="⚠️ Requisitos Importantes",
                color=0xFEE75C,  # Amarelo
            )
            requirements_embed.description = (
                f"```diff\n"
                f"+ Gamepass deve pertencer a: {order['roblox_username']}\n"
                f"+ Preço deve ser EXATAMENTE: {order['gamepass_price']:,} R$\n"
                f"+ Gamepass deve estar À VENDA\n"
                f"```"
            )
            requirements_embed.set_footer(
                text="💡 Clique em '❓ Como Criar Gamepass' se precisar de ajuda detalhada"
            )

            # Nova view sem parâmetros (persistente)
            view = GamepassConfirmView()

            await channel.send(
                content=f"<@{order['user_id']}> 🎉 **Seu pagamento foi confirmado!**",
                embeds=[
                    success_embed,
                    next_step_embed,
                    price_embed,
                    instructions_embed,
                    requirements_embed,
                ],
                view=view,
            )

        # Salva transação
        transaction = Transaction(
            payment_id=order["payment_id"],
            order_id=order_id,
            user_id=order["user_id"],
            amount=order["price_brl"],
            status="approved",
        )
        await TransactionRepository.create(transaction)

        # Atualiza estatísticas do usuário
        await UserRepository.increment_stats(
            order["user_id"], spent=order["price_brl"], robux=order["robux_amount"]
        )

        # Usa cupom
        if order.get("coupon_code"):
            await CouponRepository.use(order["coupon_code"])

        # Log
        await LogRepository.log(
            action="payment_confirmed",
            user_id=order["user_id"],
            order_id=order_id,
            details={"amount": order["price_brl"]},
            level="success",
        )

        # Envia log no canal de logs
        await self._send_log(order, "payment_confirmed")

    async def _send_log(self, order: dict, action: str) -> None:
        """Envia log para canal de logs."""
        settings = get_settings()
        log_channel = self.bot.get_channel(settings.channel_logs_id)

        if not log_channel:
            return

        if action == "payment_confirmed":
            embed = discord.Embed(
                title="💰 Pagamento Confirmado",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Pedido", value=f"`{order['order_id']}`", inline=True)
            embed.add_field(name="Usuário", value=f"<@{order['user_id']}>", inline=True)
            embed.add_field(
                name="Valor", value=f"R$ {order['price_brl']:.2f}", inline=True
            )
            embed.add_field(
                name="Robux", value=f"{order['robux_amount']:,}", inline=True
            )
            embed.add_field(
                name="Roblox", value=f"`{order['roblox_username']}`", inline=True
            )

            if order.get("coupon_code"):
                embed.add_field(
                    name="Cupom", value=f"`{order['coupon_code']}`", inline=True
                )

        elif action == "order_delivered":
            embed = discord.Embed(
                title="✅ Pedido Entregue",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Pedido", value=f"`{order['order_id']}`", inline=True)
            embed.add_field(name="Usuário", value=f"<@{order['user_id']}>", inline=True)
            embed.add_field(
                name="Robux", value=f"{order['robux_amount']:,}", inline=True
            )

        await log_channel.send(embed=embed)


class OrderActionsView(ui.View):
    """Ações do pedido com design melhorado."""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="📋 Copiar Código PIX",
        style=discord.ButtonStyle.success,
        custom_id="order:copy_pix",
        row=0,
    )
    async def copy_pix(self, interaction: discord.Interaction, button: ui.Button):
        """Envia código PIX completo para copiar."""
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket or not ticket.get("order_id"):
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        order = await OrderRepository.get_by_id(ticket["order_id"])
        if order and order.get("pix_code"):
            embed = discord.Embed(
                title="📋 Código PIX Copia e Cola",
                description=(
                    "Copie o código abaixo e cole no seu aplicativo de banco:\n\n"
                    f"```{order['pix_code']}```"
                ),
                color=0x00D166,
            )
            embed.set_footer(text="💡 Selecione todo o código acima e copie!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Código PIX não disponível.", ephemeral=True
            )

    @ui.button(
        label="🔄 Verificar Pagamento",
        style=discord.ButtonStyle.primary,
        custom_id="order:check_payment",
        row=0,
    )
    async def check_payment(self, interaction: discord.Interaction, button: ui.Button):
        """Verifica manualmente o status do pagamento."""
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket or not ticket.get("order_id"):
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        order = await OrderRepository.get_by_id(ticket["order_id"])
        if not order:
            return

        if order["status"] != OrderStatus.PENDING.value:
            status_map = {
                "paid": "✅ Pago",
                "delivered": "✅ Entregue",
                "cancelled": "❌ Cancelado",
                "expired": "⏰ Expirado",
                "processing": "🔄 Processando",
            }
            await interaction.response.send_message(
                f"Status atual: **{status_map.get(order['status'], order['status'])}**",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Verifica no Mercado Pago
        status, _ = await mercadopago_service.check_payment_status(order["payment_id"])

        if status == "approved":
            await interaction.followup.send(
                "✅ **Pagamento detectado!** Processando...", ephemeral=True
            )
        elif status == "pending":
            await interaction.followup.send(
                "⏳ **Aguardando pagamento...**\n\n"
                "Ainda não detectamos seu PIX. Após pagar, aguarde alguns segundos.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"ℹ️ Status do pagamento: `{status}`", ephemeral=True
            )

    @ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.danger,
        custom_id="order:cancel",
        row=1,
    )
    async def cancel_order(self, interaction: discord.Interaction, button: ui.Button):
        """Cancela o pedido."""
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket or not ticket.get("order_id"):
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        order = await OrderRepository.get_by_id(ticket["order_id"])
        if not order:
            return

        if order["user_id"] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Apenas o dono do pedido pode cancelar.", ephemeral=True
            )
            return

        if order["status"] != OrderStatus.PENDING.value:
            await interaction.response.send_message(
                "❌ Este pedido não pode mais ser cancelado.", ephemeral=True
            )
            return

        # Confirmação antes de cancelar
        confirm_view = ConfirmCancelView(ticket["order_id"], order["payment_id"])
        await interaction.response.send_message(
            "⚠️ **Tem certeza que deseja cancelar este pedido?**\n\n"
            "Esta ação não pode ser desfeita.",
            view=confirm_view,
            ephemeral=True,
        )


class ConfirmCancelView(ui.View):
    """Confirmação de cancelamento de pedido."""

    def __init__(self, order_id: str, payment_id: str):
        super().__init__(timeout=60)
        self.order_id = order_id
        self.payment_id = payment_id

    @ui.button(label="✅ Sim, Cancelar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        await OrderRepository.update_status(self.order_id, OrderStatus.CANCELLED)
        await mercadopago_service.cancel_payment(self.payment_id)

        embed = discord.Embed(
            title="❌ Pedido Cancelado",
            description=(
                f"O pedido `{self.order_id}` foi cancelado.\n\n"
                "Você pode iniciar uma nova compra a qualquer momento!"
            ),
            color=0xED4245,
        )
        await interaction.response.edit_message(content=None, embed=embed, view=None)

    @ui.button(label="❌ Não, Manter", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="✅ Operação cancelada. Seu pedido continua ativo!",
            view=None,
        )


class GamepassURLModal(ui.Modal, title="🎮 Enviar Link do Gamepass"):
    """Modal para cliente enviar link do gamepass criado."""

    gamepass_url = ui.TextInput(
        label="Link do Gamepass",
        placeholder="https://www.roblox.com/game-pass/123456789/...",
        style=discord.TextStyle.short,
        required=True,
        min_length=30,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Processa o link do gamepass enviado."""

        # Busca ticket e order pelo canal
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket or not ticket.get("order_id"):
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        order = await OrderRepository.get_by_id(ticket["order_id"])
        if not order:
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        # Verifica se é o dono do pedido
        if order["user_id"] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Apenas o comprador pode enviar o gamepass.", ephemeral=True
            )
            return

        # Verifica status do pedido
        if order["status"] != OrderStatus.PAID.value:
            await interaction.response.send_message(
                "❌ Este pedido não está aguardando gamepass.", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Extrai ID do gamepass do link
        url = self.gamepass_url.value.strip()

        # Padrões de URL do Roblox
        # https://www.roblox.com/game-pass/123456789/Name
        # https://roblox.com/game-pass/123456789
        gamepass_pattern = r"roblox\.com/game-pass/(\d+)"
        match = re.search(gamepass_pattern, url)

        if not match:
            await interaction.followup.send(
                "❌ **Link inválido!**\n\n"
                "O link deve ser um gamepass do Roblox.\n"
                "Exemplo: `https://www.roblox.com/game-pass/123456789/MeuGamepass`",
                ephemeral=True,
            )
            return

        gamepass_id = int(match.group(1))

        # Mensagem de processamento
        processing_embed = discord.Embed(
            title="🔄 Processando...",
            description=(
                "Validando seu gamepass...\n\n" f"🎮 **Gamepass ID:** `{gamepass_id}`"
            ),
            color=discord.Color.yellow(),
        )
        msg = await interaction.followup.send(embed=processing_embed)

        # Atualiza status para processando
        await OrderRepository.update_status(ticket["order_id"], OrderStatus.PROCESSING)

        # Salva gamepass_id no pedido
        await OrderRepository.update(ticket["order_id"], gamepass_id=gamepass_id)

        try:
            # Executa o fluxo completo de compra
            success, message = await roblox_api.full_purchase_flow(
                gamepass_id=gamepass_id,
                expected_price=order["gamepass_price"],
                expected_owner_id=order["roblox_id"],
            )

            if success:
                # ✅ Sucesso! Marca como entregue
                await OrderRepository.update_status(
                    ticket["order_id"], OrderStatus.DELIVERED
                )

                # Embed de sucesso espetacular
                success_embed = discord.Embed(
                    title="🎉 ROBUX ENTREGUES COM SUCESSO!",
                    color=0x00D166,
                )
                success_embed.description = (
                    "```diff\n"
                    "+ TRANSAÇÃO CONCLUÍDA\n"
                    "```\n\n"
                    f"💎 **{order['robux_amount']:,} Robux** foram creditados!\n\n"
                    f"**Pedido:** `{ticket['order_id']}`\n"
                    f"**Conta:** `{order['roblox_username']}`\n"
                    f"**Gamepass:** `{gamepass_id}`"
                )
                success_embed.set_thumbnail(url="https://i.imgur.com/vXHgGBN.gif")

                thanks_embed = discord.Embed(
                    title="💚 Obrigado por comprar conosco!",
                    description=(
                        "Sua compra foi concluída com sucesso!\n\n"
                        "⭐ **Gostou do atendimento?**\n"
                        "Deixe uma avaliação no canal de avaliações!\n\n"
                        "🔄 **Quer comprar mais?**\n"
                        "Feche este ticket e abra um novo carrinho!\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "📢 Indique para seus amigos e ganhe descontos!"
                    ),
                    color=0x5865F2,
                )
                thanks_embed.set_footer(text="Até a próxima! 👋")

                await msg.edit(embeds=[success_embed, thanks_embed])

                # Log de sucesso
                await LogRepository.log(
                    action="order_delivered",
                    user_id=order["user_id"],
                    order_id=ticket["order_id"],
                    details={
                        "robux": order["robux_amount"],
                        "gamepass_id": gamepass_id,
                    },
                    level="success",
                )

                logger.success(
                    f"Pedido {ticket['order_id']} entregue! "
                    f"Gamepass {gamepass_id} comprado por {order['gamepass_price']} Robux"
                )
            else:
                # ❌ Falhou - volta para status PAID
                await OrderRepository.update_status(
                    ticket["order_id"], OrderStatus.PAID
                )

                error_embed = discord.Embed(
                    title="❌ Erro na Validação",
                    description=(
                        f"**Problema:** {message}\n\n"
                        "**📋 Verifique:**\n"
                        f"• O gamepass deve custar **exatamente {order['gamepass_price']:,} Robux**\n"
                        f"• O gamepass deve pertencer à conta **{order['roblox_username']}**\n"
                        "• O gamepass deve estar **à venda**\n\n"
                        "Corrija o problema e tente novamente."
                    ),
                    color=discord.Color.red(),
                )
                await msg.edit(embed=error_embed)

                # Log de erro
                await LogRepository.log(
                    action="gamepass_validation_failed",
                    user_id=order["user_id"],
                    order_id=ticket["order_id"],
                    details={
                        "gamepass_id": gamepass_id,
                        "error": message,
                    },
                    level="warning",
                )

        except Exception as e:
            logger.error(f"Erro ao processar gamepass: {e}")

            # Volta para status PAID para permitir nova tentativa
            await OrderRepository.update_status(ticket["order_id"], OrderStatus.PAID)

            error_embed = discord.Embed(
                title="❌ Erro Interno",
                description=(
                    "Ocorreu um erro ao processar seu gamepass.\n"
                    "Por favor, tente novamente ou contate o suporte."
                ),
                color=discord.Color.red(),
            )
            await msg.edit(embed=error_embed)


class GamepassConfirmView(ui.View):
    """View para cliente enviar link do gamepass - Design profissional."""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="🎮 Enviar Link do Gamepass",
        style=discord.ButtonStyle.success,
        custom_id="gamepass:submit_url",
        row=0,
    )
    async def submit_gamepass(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        """Abre modal para enviar link do gamepass."""
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket or not ticket.get("order_id"):
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        order = await OrderRepository.get_by_id(ticket["order_id"])
        if not order:
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        if order["user_id"] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Apenas o comprador pode enviar o gamepass.", ephemeral=True
            )
            return

        if order["status"] == OrderStatus.DELIVERED.value:
            embed = discord.Embed(
                title="✅ Pedido Já Entregue",
                description=(
                    f"O pedido `{ticket['order_id']}` já foi entregue!\n\n"
                    f"💎 **{order['robux_amount']:,} Robux** foram creditados\n"
                    f"👤 Conta: **{order['roblox_username']}**"
                ),
                color=0x00D166,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if order["status"] != OrderStatus.PAID.value:
            await interaction.response.send_message(
                "❌ Este pedido não está aguardando gamepass.", ephemeral=True
            )
            return

        await interaction.response.send_modal(GamepassURLModal())

    @ui.button(
        label="❓ Tutorial Completo",
        style=discord.ButtonStyle.primary,
        custom_id="gamepass:help",
        row=0,
    )
    async def show_help(self, interaction: discord.Interaction, button: ui.Button):
        """Mostra tutorial detalhado."""
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        gamepass_price = "?"
        roblox_username = "sua conta"

        if ticket and ticket.get("order_id"):
            order = await OrderRepository.get_by_id(ticket["order_id"])
            if order:
                gamepass_price = f"{order['gamepass_price']:,}"
                roblox_username = order["roblox_username"]

        # Embed 1: Passo a passo
        tutorial_embed = discord.Embed(
            title="📚 Tutorial: Como Criar um Gamepass",
            description="Siga este guia passo a passo:",
            color=0x5865F2,
        )

        tutorial_embed.add_field(
            name="1️⃣ Acesse o Roblox Create",
            value=(
                "Vá para [create.roblox.com](https://create.roblox.com)\n"
                "e faça login na conta **" + roblox_username + "**"
            ),
            inline=False,
        )

        tutorial_embed.add_field(
            name="2️⃣ Selecione uma Experiência",
            value=(
                "Clique em qualquer experiência sua.\n"
                "*Se não tiver, crie uma nova rapidamente!*"
            ),
            inline=False,
        )

        tutorial_embed.add_field(
            name="3️⃣ Vá em Monetization → Passes",
            value=(
                "No menu lateral, clique em **Monetization**\n" "e depois em **Passes**"
            ),
            inline=False,
        )

        tutorial_embed.add_field(
            name="4️⃣ Crie o Gamepass",
            value=(
                "Clique em **Create a Pass**\n"
                "• Nome: qualquer nome\n"
                "• Imagem: qualquer imagem\n"
                f"• **Preço: {gamepass_price} Robux** ⚠️"
            ),
            inline=False,
        )

        tutorial_embed.add_field(
            name="5️⃣ Ative a Venda",
            value=(
                "Certifique-se que o toggle **'Item for Sale'**\n"
                "está **ATIVADO** (verde)"
            ),
            inline=False,
        )

        tutorial_embed.add_field(
            name="6️⃣ Copie o Link",
            value=(
                "Após criar, vá na página do gamepass no site\n"
                "Copie a URL da barra de endereço"
            ),
            inline=False,
        )

        # Embed 2: Dicas importantes
        tips_embed = discord.Embed(
            title="💡 Dicas Importantes",
            color=0xFEE75C,
        )
        tips_embed.add_field(
            name="🔗 Formato do Link",
            value=(
                "O link deve ser assim:\n"
                "`https://www.roblox.com/game-pass/123456789/Nome`"
            ),
            inline=False,
        )
        tips_embed.add_field(
            name="⚠️ Erros Comuns",
            value=(
                "• Preço diferente do indicado\n"
                "• Gamepass não está à venda\n"
                "• Gamepass criado em outra conta\n"
                "• Link de outra página (não do gamepass)"
            ),
            inline=False,
        )
        tips_embed.set_footer(text="Após criar, clique em 'Enviar Link do Gamepass'!")

        await interaction.response.send_message(
            embeds=[tutorial_embed, tips_embed], ephemeral=True
        )

    @ui.button(
        label="🔍 Verificar Meu Preço",
        style=discord.ButtonStyle.secondary,
        custom_id="gamepass:check_price",
        row=1,
    )
    async def check_price(self, interaction: discord.Interaction, button: ui.Button):
        """Mostra o preço que deve ser colocado."""
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket or not ticket.get("order_id"):
            await interaction.response.send_message(
                "❌ Pedido não encontrado!", ephemeral=True
            )
            return

        order = await OrderRepository.get_by_id(ticket["order_id"])
        if not order:
            return

        embed = discord.Embed(
            title="💎 Preço do Seu Gamepass",
            color=0xEB459E,
        )
        embed.description = (
            f"# {order['gamepass_price']:,} Robux\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Você receberá:** {order['robux_amount']:,} Robux\n"
            f"**Taxa Roblox (30%):** {order['gamepass_price'] - order['robux_amount']:,} Robux\n\n"
            f"**Conta:** `{order['roblox_username']}`\n"
            f"**Pedido:** `{order['order_id']}`"
        )
        embed.set_footer(text="⚠️ O preço deve ser EXATAMENTE este valor!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(
        label="📞 Chamar Suporte",
        style=discord.ButtonStyle.danger,
        custom_id="gamepass:support",
        row=1,
    )
    async def call_support(self, interaction: discord.Interaction, button: ui.Button):
        """Menciona admins para ajuda."""
        settings = get_settings()
        admin_role = interaction.guild.get_role(settings.role_admin_id)

        if admin_role:
            await interaction.response.send_message(
                f"{admin_role.mention}\n\n"
                f"👆 **{interaction.user.mention}** precisa de ajuda com o pedido!",
            )
        else:
            await interaction.response.send_message(
                "📞 Um administrador foi notificado e virá ajudá-lo em breve!",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(OrdersCog(bot))
