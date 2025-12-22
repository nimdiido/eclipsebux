import discord
from discord import ui
from discord.ext import commands
from loguru import logger
from src.config import get_settings
from src.database import (
    TicketRepository,
    TicketStatus,
    TicketCreate,
    LogRepository,
)


class TicketCreateButton(ui.View):
    """Botão para criar ticket."""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="🛒 Comprar Robux",
        style=discord.ButtonStyle.green,
        custom_id="ticket:create",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        """Cria um novo ticket/carrinho."""
        try:
            settings = get_settings()
            logger.info(f"🎫 Usuário {interaction.user} tentando criar ticket")

            # Verifica se já tem ticket aberto
            existing = await TicketRepository.get_user_open_ticket(interaction.user.id)
            if existing:
                try:
                    channel = interaction.guild.get_channel(existing["channel_id"])
                    if channel:
                        await interaction.response.send_message(
                            f"❌ Você já tem um ticket aberto: {channel.mention}",
                            ephemeral=True,
                        )
                        logger.info(
                            f"⚠️ Usuário {interaction.user} já tem ticket aberto"
                        )
                        return
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao verificar ticket existente: {e}")

            await interaction.response.defer(ephemeral=True)
            logger.info(f"✅ Criando canal de ticket para {interaction.user}")

            # Cria o canal do ticket
            category = interaction.guild.get_channel(settings.category_tickets_id)
            if not category:
                logger.error(
                    f"❌ Categoria de tickets não encontrada: {settings.category_tickets_id}"
                )
                await interaction.followup.send(
                    "❌ Categoria de tickets não configurada. Contate um administrador.",
                    ephemeral=True,
                )
                return

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True,
                ),
            }

            # Adiciona admins
            admin_role = interaction.guild.get_role(settings.role_admin_id)
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                )

            channel = await interaction.guild.create_text_channel(
                name=f"🛒│{interaction.user.name[:20]}",
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user.name} | ID: {interaction.user.id}",
            )
            logger.success(f"✅ Canal criado: {channel.name} (ID: {channel.id})")

            # Salva no banco
            ticket_data = TicketCreate(
                user_id=interaction.user.id,
                channel_id=channel.id,
                subject="Compra de Robux",
            )
            ticket_id = await TicketRepository.create(ticket_data)
            logger.success(f"✅ Ticket salvo no banco: {ticket_id}")

            # Envia mensagem de boas-vindas profissional
            settings = get_settings()
            price_per_1k = settings.price_per_1000_robux / 100

            # Banner/Header
            header_embed = discord.Embed(
                color=0x00D166,  # Verde vibrante
            )
            header_embed.set_image(url="https://i.imgur.com/8QXmZPR.png")  # Banner

            # Embed principal de boas-vindas
            welcome_embed = discord.Embed(
                title="<:robux:1234567890> Bem-vindo à Loja de Robux!",
                description=(
                    f"Olá {interaction.user.mention}! 👋\n\n"
                    "Estamos felizes em te atender! Aqui você pode comprar Robux "
                    "de forma **rápida**, **segura** e **automática**."
                ),
                color=0x5865F2,  # Blurple do Discord
            )
            welcome_embed.set_thumbnail(url=interaction.user.display_avatar.url)

            # Embed de preços
            price_embed = discord.Embed(
                title="💰 Tabela de Preços",
                color=0xFEE75C,  # Amarelo
            )

            # Calcula exemplos de preços
            examples = [100, 500, 1000, 2000, 5000, 10000]
            price_table = ""
            for robux in examples:
                price = settings.calculate_price(robux)
                price_table += f"**{robux:,}** R$ → `R$ {price:.2f}`\n"

            price_embed.add_field(
                name="📊 Exemplos",
                value=price_table,
                inline=True,
            )
            price_embed.add_field(
                name="ℹ️ Informações",
                value=(
                    f"💵 **R$ {price_per_1k:.2f}** / 1.000 R$\n"
                    f"📉 Mínimo: **{settings.min_robux_amount:,}** R$\n"
                    f"📈 Máximo: **{settings.max_robux_amount:,}** R$\n"
                    "⚡ Entrega: **Instantânea**"
                ),
                inline=True,
            )

            # Embed de como funciona
            steps_embed = discord.Embed(
                title="📋 Como Funciona?",
                description=(
                    "```\n"
                    "1️⃣ Clique em 'Iniciar Compra'\n"
                    "2️⃣ Informe quantidade e seu usuário Roblox\n"
                    "3️⃣ Pague o PIX gerado\n"
                    "4️⃣ Crie um Gamepass no valor indicado\n"
                    "5️⃣ Envie o link e receba seus Robux!\n"
                    "```"
                ),
                color=0x5865F2,
            )
            steps_embed.add_field(
                name="🔒 Segurança Garantida",
                value=(
                    "• Método oficial via Gamepass\n"
                    "• Não pedimos senha ou cookie\n"
                    "• Pagamento seguro via PIX\n"
                    "• Entrega verificada automaticamente"
                ),
                inline=False,
            )
            steps_embed.set_footer(
                text=f"🎫 Ticket #{ticket_id} • Atendimento 24/7",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
            )

            view = TicketActionsView()
            await channel.send(
                embeds=[welcome_embed, price_embed, steps_embed], view=view
            )
            logger.success(f"✅ Mensagem inicial enviada no ticket {ticket_id}")

            await interaction.followup.send(
                f"✅ Seu carrinho foi criado: {channel.mention}", ephemeral=True
            )

            # Log
            await LogRepository.log(
                action="ticket_created",
                user_id=interaction.user.id,
                details={"ticket_id": ticket_id, "channel_id": channel.id},
            )

        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO ao criar ticket: {e}")
            logger.exception(e)  # Mostra traceback completo
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        f"❌ Erro ao criar ticket: {str(e)}\nContate um administrador.",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ Erro ao criar ticket: {str(e)}\nContate um administrador.",
                        ephemeral=True,
                    )
            except Exception:
                logger.error("❌ Não foi possível enviar mensagem de erro ao usuário")


class TicketActionsView(ui.View):
    """Ações do ticket."""

    def __init__(self, ticket_id: str = None):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

        # Se ticket_id foi fornecido, atualiza os custom_ids
        if ticket_id:
            for item in self.children:
                if isinstance(item, ui.Button):
                    # Mantém o prefixo mas não inclui ticket_id no custom_id
                    # pois o custom_id deve ser fixo para persistência
                    pass

    @ui.button(
        label="💰 Iniciar Compra",
        style=discord.ButtonStyle.green,
        custom_id="ticket:buy",
        row=0,
    )
    async def start_buy(self, interaction: discord.Interaction, button: ui.Button):
        """Abre modal para iniciar compra."""
        # Busca ticket pelo canal
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket não encontrado!", ephemeral=True
            )
            return

        modal = BuyRobuxModal(ticket["ticket_id"])
        await interaction.response.send_modal(modal)

    @ui.button(
        label="🎟️ Usar Cupom",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket:coupon",
        row=0,
    )
    async def use_coupon(self, interaction: discord.Interaction, button: ui.Button):
        """Abre modal para usar cupom."""
        # Busca ticket pelo canal
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket não encontrado!", ephemeral=True
            )
            return

        modal = CouponModal(ticket["ticket_id"])
        await interaction.response.send_modal(modal)

    @ui.button(
        label="❓ Ajuda", style=discord.ButtonStyle.gray, custom_id="ticket:help", row=0
    )
    async def show_help(self, interaction: discord.Interaction, button: ui.Button):
        """Mostra ajuda."""
        settings = get_settings()

        price_per_1k = settings.price_per_1000_robux / 100

        embed = discord.Embed(
            title="❓ Central de Ajuda",
            description=(
                "**💰 Preços:**\n"
                f"• 1.000 Robux = R$ {price_per_1k:.2f}\n"
                f"• Mínimo: {settings.min_robux_amount} Robux\n"
                f"• Máximo: {settings.max_robux_amount} Robux\n\n"
                "**📋 Processo de Entrega:**\n"
                "Utilizamos o sistema de **Gamepasses** do Roblox.\n"
                "Após o pagamento, você compra um gamepass especial\n"
                "e recebe os Robux diretamente na sua conta!\n\n"
                "**⏰ Tempo de Entrega:**\n"
                "Após pagamento confirmado: **Instantâneo**\n\n"
                "**🔒 Segurança:**\n"
                "• Método 100% seguro e permitido pelo Roblox\n"
                "• Não pedimos sua senha ou cookie\n"
                "• Pagamento via PIX com confirmação automática"
            ),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(
        label="🔴 Fechar Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
        row=1,
    )
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        """Fecha o ticket."""
        settings = get_settings()

        # Busca ticket pelo canal
        ticket = await TicketRepository.get_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket não encontrado!", ephemeral=True
            )
            return

        # Verifica permissão
        is_owner = interaction.user.id == ticket["user_id"]
        is_admin = any(r.id == settings.role_admin_id for r in interaction.user.roles)

        if not is_owner and not is_admin:
            await interaction.response.send_message(
                "❌ Apenas o dono do ticket ou admins podem fechar.", ephemeral=True
            )
            return

        # Confirmação
        view = ConfirmCloseView(ticket["ticket_id"], interaction.user.id)
        await interaction.response.send_message(
            "⚠️ Tem certeza que deseja fechar este ticket?", view=view, ephemeral=True
        )


class BuyRobuxModal(ui.Modal, title="💰 Comprar Robux"):
    """Modal para iniciar compra."""

    robux_amount = ui.TextInput(
        label="Quantidade de Robux",
        placeholder="Ex: 1000",
        min_length=1,
        max_length=10,
        required=True,
    )

    roblox_username = ui.TextInput(
        label="Seu usuário do Roblox",
        placeholder="Ex: PlayerName123",
        min_length=3,
        max_length=50,
        required=True,
    )

    def __init__(self, ticket_id: str):
        super().__init__()
        self.ticket_id = ticket_id

    async def on_submit(self, interaction: discord.Interaction):
        # Valida quantidade
        try:
            amount = int(self.robux_amount.value.replace(".", "").replace(",", ""))
        except ValueError:
            await interaction.response.send_message(
                "❌ Quantidade inválida. Digite apenas números.", ephemeral=True
            )
            return

        settings = get_settings()

        if amount < settings.min_robux_amount:
            await interaction.response.send_message(
                f"❌ Mínimo de {settings.min_robux_amount} Robux.", ephemeral=True
            )
            return

        if amount > settings.max_robux_amount:
            await interaction.response.send_message(
                f"❌ Máximo de {settings.max_robux_amount} Robux.", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Processa a compra via OrdersCog
        cog = interaction.client.get_cog("OrdersCog")
        if cog:
            await cog.process_order(
                interaction, self.ticket_id, amount, self.roblox_username.value.strip()
            )


class CouponModal(ui.Modal, title="🎟️ Usar Cupom"):
    """Modal para usar cupom."""

    coupon_code = ui.TextInput(
        label="Código do Cupom",
        placeholder="Ex: DESCONTO10",
        min_length=3,
        max_length=30,
        required=True,
    )

    def __init__(self, ticket_id: str):
        super().__init__()
        self.ticket_id = ticket_id

    async def on_submit(self, interaction: discord.Interaction):
        from src.database import CouponRepository

        code = self.coupon_code.value.strip().upper()

        # Verifica cupom
        valid, message, discount = await CouponRepository.validate(code, 1000)

        if valid:
            embed = discord.Embed(
                title="✅ Cupom Válido!",
                description=(
                    f"**Código:** `{code}`\n"
                    f"**Desconto:** {discount * 100:.0f}%\n\n"
                    "O cupom será aplicado automaticamente na sua compra!"
                ),
                color=discord.Color.green(),
            )

            # Salva cupom no ticket (em memória, será usado na compra)
            interaction.client.ticket_coupons = getattr(
                interaction.client, "ticket_coupons", {}
            )
            interaction.client.ticket_coupons[self.ticket_id] = {
                "code": code,
                "discount": discount,
            }
        else:
            embed = discord.Embed(
                title="❌ Cupom Inválido",
                description=message,
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfirmCloseView(ui.View):
    """Confirmação para fechar ticket."""

    def __init__(self, ticket_id: str, user_id: int):
        super().__init__(timeout=60)
        self.ticket_id = ticket_id
        self.user_id = user_id

    @ui.button(label="✅ Sim, Fechar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return

        await interaction.response.defer()

        # Atualiza status
        await TicketRepository.update_status(
            self.ticket_id, TicketStatus.CLOSED, closed_by=interaction.user.id
        )

        # Log
        await LogRepository.log(
            action="ticket_closed",
            user_id=interaction.user.id,
            details={"ticket_id": self.ticket_id},
        )

        embed = discord.Embed(
            title="🔒 Ticket Fechado",
            description="Este ticket será deletado em 5 segundos...",
            color=discord.Color.red(),
        )
        await interaction.channel.send(embed=embed)

        # Deleta o canal após 5 segundos
        import asyncio as aio

        await aio.sleep(5)

        try:
            await interaction.channel.delete(reason="Ticket fechado")
        except Exception:
            pass

    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return

        await interaction.response.edit_message(
            content="✅ Operação cancelada.", view=None
        )


async def setup_ticket_panel(bot: commands.Bot) -> None:
    """Configura o painel de tickets profissional."""
    settings = get_settings()

    channel = bot.get_channel(settings.channel_vendas_id)
    if not channel:
        logger.warning("⚠️ Canal de vendas não encontrado")
        return

    # Verifica se já existe mensagem do painel
    async for message in channel.history(limit=10):
        if message.author == bot.user and message.embeds:
            for embed in message.embeds:
                if embed.title and "Loja" in embed.title:
                    # Adiciona view persistente
                    view = TicketCreateButton()
                    await message.edit(view=view)
                    logger.info("✅ Painel de tickets atualizado")
                    return

    # Calcula preço para exibição
    price_per_1k = settings.price_per_1000_robux / 100

    # ═══════════════════════════════════════════════════════════
    # EMBED 1: Header/Banner
    # ═══════════════════════════════════════════════════════════
    banner_embed = discord.Embed(color=0x5865F2)
    banner_embed.set_image(url="https://i.imgur.com/KRK5Fz0.png")  # Banner da loja

    # ═══════════════════════════════════════════════════════════
    # EMBED 2: Informações Principais
    # ═══════════════════════════════════════════════════════════
    main_embed = discord.Embed(
        title="<:robux:1234567890> Loja Oficial de Robux",
        description=(
            "Compre Robux de forma **rápida**, **segura** e com\n"
            "**entrega automática** via Gamepass!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x00D166,
    )

    main_embed.add_field(
        name="💰 Preço",
        value=f"**R$ {price_per_1k:.2f}** / 1.000 R$",
        inline=True,
    )
    main_embed.add_field(
        name="⚡ Entrega",
        value="**Instantânea**",
        inline=True,
    )
    main_embed.add_field(
        name="💳 Pagamento",
        value="**PIX**",
        inline=True,
    )

    # ═══════════════════════════════════════════════════════════
    # EMBED 3: Vantagens
    # ═══════════════════════════════════════════════════════════
    features_embed = discord.Embed(
        title="✨ Por que comprar conosco?",
        color=0x5865F2,
    )
    features_embed.add_field(
        name="🔒 100% Seguro",
        value="Método oficial via Gamepass\nNão pedimos senha",
        inline=True,
    )
    features_embed.add_field(
        name="🤖 Automático",
        value="Sistema 100% automatizado\nSem esperar atendente",
        inline=True,
    )
    features_embed.add_field(
        name="💎 Melhor Preço",
        value="Valores competitivos\nDescontos com cupom",
        inline=True,
    )

    # ═══════════════════════════════════════════════════════════
    # EMBED 4: Call to Action
    # ═══════════════════════════════════════════════════════════
    cta_embed = discord.Embed(
        description=(
            "```\n" "🛒 Clique no botão abaixo para iniciar sua compra!\n" "```"
        ),
        color=0xFEE75C,
    )
    cta_embed.set_footer(
        text="🕐 Atendimento 24/7 • ⭐ +1000 clientes satisfeitos",
    )

    view = TicketCreateButton()
    await channel.send(
        embeds=[banner_embed, main_embed, features_embed, cta_embed], view=view
    )
    logger.success("✅ Painel de tickets criado")


class TicketsCog(commands.Cog):
    """Cog de gerenciamento de tickets."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    """Registra a cog de tickets."""
    await bot.add_cog(TicketsCog(bot))
