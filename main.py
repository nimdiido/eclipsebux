import discord
from discord.ext import commands
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_settings
from src.database import db
from src.services import roblox_api
from src.cogs.tickets import TicketCreateButton, setup_ticket_panel


class RobuxBot(commands.Bot):
    """Bot principal de vendas de Robux."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.settings = get_settings()
        self.ticket_coupons = {}  # Cache de cupons por ticket

    async def setup_hook(self):
        """Configuração inicial do bot."""
        logger.info("🔧 Iniciando configuração do bot...")

        # Conecta ao PostgreSQL
        await db.connect(self.settings.database_url)

        # Valida cookie do Roblox
        valid, message = await roblox_api.validate_cookie()
        if valid:
            logger.success(f"🎮 Roblox: {message}")
        else:
            logger.warning(f"⚠️ Roblox: {message}")

        # Registra views persistentes
        self.add_view(TicketCreateButton())
        from src.cogs.tickets import TicketActionsView
        from src.cogs.orders import OrderActionsView, GamepassConfirmView

        self.add_view(TicketActionsView())
        self.add_view(OrderActionsView())
        self.add_view(GamepassConfirmView())
        # Views de tickets são adicionadas dinamicamente

        # Carrega cogs
        cogs = [
            "src.cogs.orders",
            "src.cogs.admin",
            "src.cogs.user",
            "src.cogs.tickets",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Cog carregada: {cog}")
            except Exception as e:
                logger.error(f"❌ Erro ao carregar {cog}: {e}")

        # Sincroniza comandos
        try:
            guild = discord.Object(id=self.settings.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.success(f"✅ {len(synced)} comandos sincronizados")
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar comandos: {e}")

    async def on_ready(self):
        """Evento quando o bot está pronto."""
        logger.success(f"🤖 Bot conectado como {self.user}")
        logger.info(f"📊 Servidores: {len(self.guilds)}")

        # Configura status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="💎 Loja de Robux"
            )
        )

        # Configura painel de tickets
        await asyncio.sleep(2)  # Aguarda cache carregar
        await setup_ticket_panel(self)

    async def on_guild_join(self, guild: discord.Guild):
        """Evento quando bot entra em um servidor."""
        logger.info(f"➕ Entrou no servidor: {guild.name} ({guild.id})")

    async def on_guild_remove(self, guild: discord.Guild):
        """Evento quando bot sai de um servidor."""
        logger.info(f"➖ Saiu do servidor: {guild.name} ({guild.id})")

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handler global de erros."""
        if isinstance(error, commands.CommandNotFound):
            return

        logger.error(f"❌ Erro no comando: {error}")

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Você não tem permissão para isso!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argumento obrigatório: `{error.param.name}`")
        else:
            await ctx.send("❌ Ocorreu um erro. Tente novamente.")

    async def close(self):
        """Cleanup ao fechar o bot."""
        logger.info("🔌 Desconectando...")

        await roblox_api.close()
        await db.disconnect()

        await super().close()


def setup_logging():
    """Configura o sistema de logs."""
    logger.remove()

    # Console
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
        colorize=True,
    )

    # Arquivo
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="00:00",
        retention="7 days",
    )


async def main():
    """Função principal."""
    setup_logging()

    logger.info("=" * 50)
    logger.info("🚀 Iniciando Bot de Vendas de Robux")
    logger.info("=" * 50)

    bot = RobuxBot()

    try:
        await bot.start(bot.settings.discord_token)
    except KeyboardInterrupt:
        logger.info("⏹️ Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
