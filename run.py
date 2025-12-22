import sys
import os

# Script para rodar o bot
if __name__ == "__main__":
    # Adiciona o diretório raiz ao path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print(
        """
    ╔═══════════════════════════════════════════════════╗
    ║        🎮 BOT DE VENDAS DE ROBUX 🎮               ║
    ╠═══════════════════════════════════════════════════╣
    ║  Iniciando...                                     ║
    ║  Certifique-se de ter configurado o .env          ║
    ╚═══════════════════════════════════════════════════╝
    """
    )

    # Importa e executa
    from main import main
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado!")
