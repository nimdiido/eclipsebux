<h1 align="center">
  <br>
  <img src="https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord Bot">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <br>
  🎮 Robux Sales Bot
  <br>
</h1>

<p align="center">
  <strong>A professional Discord bot for automated Robux sales with PIX payment integration and secure Gamepass delivery.</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/discord.py-2.3+-5865F2?style=flat-square" alt="discord.py">
</p>

---

## 📋 Overview

This project is a **full-featured Discord bot** designed to automate the sale and delivery of Robux (Roblox virtual currency). It integrates with **Mercado Pago** for PIX payments (Brazilian instant payment system) and the **Roblox API** for secure Gamepass-based delivery.

> ⚠️ **Note:** This is a portfolio project demonstrating backend development, API integration, and asynchronous programming skills. Robux trading involves Roblox's Terms of Service considerations.

## ✨ Features

### Payment & Transactions
- 🔐 **Automated PIX Payments** - Integration with Mercado Pago API for instant Brazilian PIX payments
- ⏱️ **Real-time Payment Verification** - Automatic polling for payment confirmation
- 🧾 **Transaction Logging** - Complete audit trail of all transactions

### Roblox Integration
- 🎮 **Secure Gamepass Delivery** - Uses Roblox's official Gamepass system (ToS-compliant method)
- 👤 **User Verification** - Validates Roblox usernames and IDs via API
- 🍪 **Session Management** - Secure handling of Roblox authentication

### Discord Experience
- 🎫 **Ticket System** - Automated ticket creation for each purchase
- 🎨 **Modern UI** - Discord Components V2 (buttons, modals, dropdowns)
- 🏷️ **Coupon System** - Discount codes with usage limits and expiration
- 📊 **Admin Dashboard** - Statistics, order management, and user controls

### Technical Highlights
- ⚡ **Fully Asynchronous** - Built with `asyncio` for high concurrency
- 🗄️ **PostgreSQL Database** - Robust data persistence with SQLAlchemy ORM
- 🔄 **Persistent Views** - Bot UI survives restarts
- 📝 **Structured Logging** - Detailed logs with Loguru

## 🛠 Tech Stack

| Category | Technologies |
|----------|-------------|
| **Runtime** | Python 3.10+ |
| **Bot Framework** | discord.py 2.3+ |
| **Database** | PostgreSQL with asyncpg |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Payment Gateway** | Mercado Pago SDK |
| **HTTP Client** | aiohttp, httpx |
| **Configuration** | Pydantic Settings |
| **Logging** | Loguru |
| **Validation** | Pydantic |

## 🏗 Architecture

```
robux/
├── main.py                    # Bot initialization and event handlers
├── run.py                     # Entry point with error handling
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
│
└── src/
    ├── config/
    │   └── settings.py        # Centralized configuration with Pydantic
    │
    ├── database/
    │   ├── connection.py      # Async PostgreSQL connection pool
    │   ├── models.py          # SQLAlchemy ORM models
    │   └── repositories.py    # Data access layer (Repository Pattern)
    │
    ├── services/
    │   ├── payment_service.py # Mercado Pago API integration
    │   └── roblox_service.py  # Roblox API client with rate limiting
    │
    └── cogs/
        ├── tickets.py         # Ticket system and purchase flow
        ├── orders.py          # Order management and delivery
        ├── admin.py           # Administrative commands
        └── user.py            # User-facing commands
```

### Design Patterns Used

- **Repository Pattern** - Abstracts database operations
- **Service Layer** - Business logic separation
- **Dependency Injection** - Centralized configuration via Pydantic
- **Async/Await** - Non-blocking I/O for all external calls
- **Rate Limiting** - Prevents API throttling with aiolimiter

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 13+
- Discord Bot Token ([Developer Portal](https://discord.com/developers/applications))
- Mercado Pago Account ([Developers](https://www.mercadopago.com.br/developers))
- Roblox Account with a published game

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/robux-bot.git
cd robux-bot

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## ⚙️ Configuration

Edit the `.env` file with your credentials:

```env
# Discord
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/robux_bot

# Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=your_access_token

# Roblox
ROBLOX_COOKIE=your_roblosecurity_cookie
ROBLOX_USER_ID=your_user_id
ROBLOX_UNIVERSE_ID=your_game_universe_id
```

### Discord Bot Setup

1. Create application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable **Privileged Gateway Intents**:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
3. Generate invite link with `Administrator` permission
4. Invite bot to your server

## 🚀 Usage

```bash
# Start the bot
python main.py
```

### Commands

#### User Commands
| Command | Description |
|---------|-------------|
| `/perfil` | View your profile and purchase history |
| `/pedidos` | List your orders |
| `/preco <amount>` | Calculate price for Robux amount |
| `/verificar_usuario <username>` | Verify a Roblox username |
| `/ajuda` | Display help information |

#### Admin Commands
| Command | Description |
|---------|-------------|
| `/cupom_criar <code> <discount>` | Create discount coupon |
| `/cupom_desativar <code>` | Deactivate coupon |
| `/pedido <id>` | View order details |
| `/entregar <id>` | Manual delivery |
| `/reembolsar <id>` | Process refund |
| `/stats` | View sales statistics |
| `/top_compradores` | Top buyers leaderboard |
| `/setup_painel` | Initialize sales panel |

### Purchase Flow

```
1. Customer clicks "Buy Robux" → Ticket created
2. Customer enters amount + Roblox username
3. PIX payment generated automatically
4. Payment verified in real-time
5. Gamepass link provided to customer
6. Customer purchases Gamepass → Robux delivered
```

## 🔒 Security Considerations

- **Environment Variables** - All secrets stored in `.env` (gitignored)
- **Cookie Security** - Roblox cookie never logged or exposed
- **Input Validation** - Pydantic validators for all user input
- **Rate Limiting** - Prevents API abuse
- **Gamepass Method** - Uses Roblox's official, ToS-compliant delivery method

## 📊 Database Schema

```sql
-- Core entities
Users       → Discord/Roblox user data, purchase history
Orders      → Transaction records with status tracking
Tickets     → Support ticket management
Coupons     → Discount codes with usage limits
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

For questions or suggestions, please open an issue or reach out via Discord.

---

<p align="center">
  <sub>Built with ❤️ using Python and discord.py</sub>
</p>
