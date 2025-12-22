import discord
from discord import app_commands
from discord.ext import commands

from src.config import get_settings
from src.database import UserRepository, OrderRepository
from src.services import roblox_api


class UserCog(commands.Cog):
    """Comandos de usuário."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="perfil", description="Mostra seu perfil")
    async def profile(self, interaction: discord.Interaction):
        """Mostra o perfil do usuário."""
        user = await UserRepository.get_by_id(interaction.user.id)

        if not user:
            await interaction.response.send_message(
                "❌ Você ainda não fez nenhuma compra!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"👤 Perfil de {interaction.user.display_name}",
            color=discord.Color.blue(),
        )

        if user.get("roblox_username"):
            embed.add_field(
                name="🎮 Roblox", value=f"`{user['roblox_username']}`", inline=True
            )

        embed.add_field(
            name="📦 Pedidos", value=str(user.get("orders_count", 0)), inline=True
        )
        embed.add_field(
            name="💰 Total Gasto",
            value=f"R$ {user.get('total_spent', 0):,.2f}",
            inline=True,
        )
        embed.add_field(
            name="💎 Robux Comprados",
            value=f"{user.get('total_robux_bought', 0):,}",
            inline=True,
        )

        if user.get("is_vip"):
            embed.add_field(name="⭐ VIP", value="Sim", inline=True)

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(
            text=f"Cliente desde {user['created_at'].strftime('%d/%m/%Y')}"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pedidos", description="Lista seus pedidos recentes")
    async def my_orders(self, interaction: discord.Interaction):
        """Lista pedidos do usuário."""
        orders = await OrderRepository.get_user_orders(interaction.user.id, 5)

        if not orders:
            await interaction.response.send_message(
                "❌ Você ainda não tem pedidos!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📦 Seus Pedidos Recentes", color=discord.Color.blue()
        )

        status_emoji = {
            "pending": "⏳",
            "paid": "💰",
            "processing": "🔄",
            "delivered": "✅",
            "cancelled": "❌",
            "refunded": "💸",
            "expired": "⏰",
        }

        for order in orders:
            status = order.get("status", "unknown")
            emoji = status_emoji.get(status, "❓")

            embed.add_field(
                name=f"{emoji} {order['order_id']}",
                value=(
                    f"💎 {order['robux_amount']:,} Robux\n"
                    f"💰 R$ {order['price_brl']:.2f}\n"
                    f"📅 {order['created_at'].strftime('%d/%m/%Y %H:%M')}"
                ),
                inline=True,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="verificar_usuario", description="Verifica se um usuário Roblox existe"
    )
    @app_commands.describe(username="Nome de usuário do Roblox")
    async def verify_user(self, interaction: discord.Interaction, username: str):
        """Verifica usuário do Roblox."""
        await interaction.response.defer(ephemeral=True)

        user = await roblox_api.get_user_by_username(username)

        if user:
            embed = discord.Embed(
                title="✅ Usuário Encontrado", color=discord.Color.green()
            )
            embed.add_field(name="Nome", value=user["name"], inline=True)
            embed.add_field(name="Display Name", value=user["displayName"], inline=True)
            embed.add_field(name="ID", value=str(user["id"]), inline=True)
            embed.set_thumbnail(
                url=f"https://www.roblox.com/headshot-thumbnail/image?userId={user['id']}&width=150&height=150"
            )
        else:
            embed = discord.Embed(
                title="❌ Usuário Não Encontrado",
                description=f"O usuário `{username}` não existe no Roblox.",
                color=discord.Color.red(),
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="preco", description="Calcula o preço de uma quantidade de Robux"
    )
    @app_commands.describe(quantidade="Quantidade de Robux")
    async def price_check(self, interaction: discord.Interaction, quantidade: int):
        """Calcula preço."""
        settings = get_settings()

        if quantidade < settings.min_robux_amount:
            await interaction.response.send_message(
                f"❌ Mínimo de {settings.min_robux_amount} Robux!", ephemeral=True
            )
            return

        if quantidade > settings.max_robux_amount:
            await interaction.response.send_message(
                f"❌ Máximo de {settings.max_robux_amount} Robux!", ephemeral=True
            )
            return

        price = settings.calculate_price(quantidade)

        embed = discord.Embed(
            title="💰 Calculadora de Preço", color=discord.Color.green()
        )
        embed.add_field(name="💎 Robux", value=f"{quantidade:,}", inline=True)
        embed.add_field(name="💵 Preço", value=f"R$ {price:.2f}", inline=True)
        embed.set_footer(text="Use /comprar para adquirir!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ajuda", description="Mostra informações de ajuda")
    async def help_command(self, interaction: discord.Interaction):
        """Mostra ajuda."""
        settings = get_settings()
        price_per_1k = settings.price_per_1000_robux / 100

        embed = discord.Embed(
            title="❓ Central de Ajuda",
            description="Bem-vindo à nossa loja de Robux!",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="💰 Como Comprar",
            value=(
                "1. Vá no canal de vendas e clique em 'Comprar Robux'\n"
                "2. Informe a quantidade desejada e seu usuário Roblox\n"
                "3. Pague o PIX gerado automaticamente\n"
                "4. Compre o gamepass que criaremos\n"
                "5. Pronto! Robux na sua conta!"
            ),
            inline=False,
        )

        embed.add_field(
            name="💵 Preços",
            value=(
                f"• 1.000 Robux = R$ {price_per_1k:.2f}\n"
                f"• Mínimo: {settings.min_robux_amount} Robux\n"
                f"• Máximo: {settings.max_robux_amount:,} Robux"
            ),
            inline=True,
        )

        embed.add_field(
            name="⏰ Entrega",
            value=(
                "• Após pagamento: Instantânea\n" "• Método: Gamepass\n" "• 100% Seguro"
            ),
            inline=True,
        )

        embed.add_field(
            name="🔧 Comandos",
            value=(
                "`/perfil` - Seu perfil\n"
                "`/pedidos` - Seus pedidos\n"
                "`/preco` - Calculadora\n"
                "`/verificar_usuario` - Verifica Roblox"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCog(bot))
