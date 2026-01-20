<h1 align="center">
  <br>
  <img src="https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord Bot">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <br>
  🎮 Bot de Vendas de Robux
  <br>
</h1>

<p align="center">
  <strong>Bot profissional para Discord com vendas automatizadas de Robux, integração com pagamentos PIX e entrega segura via Gamepass.</strong>
</p>

<p align="center">
  <a href="#-funcionalidades">Funcionalidades</a> •
  <a href="#-tecnologias">Tecnologias</a> •
  <a href="#-arquitetura">Arquitetura</a> •
  <a href="#-instalação">Instalação</a> •
  <a href="#-configuração">Configuração</a> •
  <a href="#-uso">Uso</a> •
  <a href="#-licença">Licença</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Produção-brightgreen?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/Licença-MIT-blue?style=flat-square" alt="Licença">
  <img src="https://img.shields.io/badge/discord.py-2.3+-5865F2?style=flat-square" alt="discord.py">
</p>

---

## 📋 Visão Geral

Este projeto é um **bot completo para Discord** desenvolvido para automatizar a venda e entrega de Robux (moeda virtual do Roblox). Integra-se com o **Mercado Pago** para pagamentos via PIX e com a **API do Roblox** para entrega segura via Gamepass.

> ⚠️ **Nota:** Este é um projeto de portfólio que demonstra habilidades em desenvolvimento backend, integração com APIs e programação assíncrona. A comercialização de Robux envolve considerações sobre os Termos de Serviço do Roblox.

## ✨ Funcionalidades

### Pagamentos e Transações

- 🔐 **Pagamentos PIX Automatizados** - Integração com API do Mercado Pago para pagamentos instantâneos
- ⏱️ **Verificação em Tempo Real** - Polling automático para confirmação de pagamentos
- 🧾 **Registro de Transações** - Histórico completo de todas as operações

### Integração com Roblox

- 🎮 **Entrega Segura via Gamepass** - Utiliza o sistema oficial de Gamepass do Roblox
- 👤 **Verificação de Usuários** - Valida usernames e IDs do Roblox via API
- 🍪 **Gerenciamento de Sessão** - Manipulação segura da autenticação Roblox

### Experiência no Discord

- 🎫 **Sistema de Tickets** - Criação automática de tickets para cada compra
- 🎨 **Interface Moderna** - Discord Components V2 (botões, modais, dropdowns)
- 🏷️ **Sistema de Cupons** - Códigos de desconto com limite de uso e expiração
- 📊 **Painel Administrativo** - Estatísticas, gerenciamento de pedidos e controles

### Destaques Técnicos

- ⚡ **Totalmente Assíncrono** - Construído com `asyncio` para alta concorrência
- 🗄️ **Banco de Dados PostgreSQL** - Persistência robusta com SQLAlchemy ORM
- 🔄 **Views Persistentes** - Interface do bot sobrevive a reinicializações
- 📝 **Logging Estruturado** - Logs detalhados com Loguru

## 🛠 Tecnologias

| Categoria                | Tecnologias            |
| ------------------------ | ---------------------- |
| **Runtime**              | Python 3.10+           |
| **Framework do Bot**     | discord.py 2.3+        |
| **Banco de Dados**       | PostgreSQL com asyncpg |
| **ORM**                  | SQLAlchemy 2.0 (async) |
| **Gateway de Pagamento** | Mercado Pago SDK       |
| **Cliente HTTP**         | aiohttp, httpx         |
| **Configuração**         | Pydantic Settings      |
| **Logging**              | Loguru                 |
| **Validação**            | Pydantic               |

## 🏗 Arquitetura

```
robux/
├── main.py                    # Inicialização do bot e event handlers
├── run.py                     # Ponto de entrada com tratamento de erros
├── requirements.txt           # Dependências Python
├── .env.example               # Template de variáveis de ambiente
│
└── src/
    ├── config/
    │   └── settings.py        # Configuração centralizada com Pydantic
    │
    ├── database/
    │   ├── connection.py      # Pool de conexões async do PostgreSQL
    │   ├── models.py          # Modelos ORM do SQLAlchemy
    │   └── repositories.py    # Camada de acesso a dados (Repository Pattern)
    │
    ├── services/
    │   ├── payment_service.py # Integração com API do Mercado Pago
    │   └── roblox_service.py  # Cliente da API do Roblox com rate limiting
    │
    └── cogs/
        ├── tickets.py         # Sistema de tickets e fluxo de compra
        ├── orders.py          # Gerenciamento de pedidos e entregas
        ├── admin.py           # Comandos administrativos
        └── user.py            # Comandos para usuários
```

### Padrões de Projeto Utilizados

- **Repository Pattern** - Abstração das operações de banco de dados
- **Service Layer** - Separação da lógica de negócios
- **Dependency Injection** - Configuração centralizada via Pydantic
- **Async/Await** - I/O não-bloqueante para todas as chamadas externas
- **Rate Limiting** - Previne throttling de APIs com aiolimiter

## 📦 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 13+
- Token do Bot Discord ([Developer Portal](https://discord.com/developers/applications))
- Conta no Mercado Pago ([Developers](https://www.mercadopago.com.br/developers))
- Conta Roblox com um jogo publicado

### Configuração do Ambiente

```bash
# Clone o repositório
git clone https://github.com/yourusername/robux-bot.git
cd robux-bot

# Crie o ambiente virtual
python -m venv venv

# Ative (Windows)
.\venv\Scripts\activate

# Ative (Linux/macOS)
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Copie o template de ambiente
cp .env.example .env
```

## ⚙️ Configuração

Edite o arquivo `.env` com suas credenciais:

```env
# Discord
DISCORD_TOKEN=seu_token_do_bot
DISCORD_GUILD_ID=id_do_seu_servidor

# Banco de Dados
DATABASE_URL=postgresql+asyncpg://usuario:senha@localhost:5432/robux_bot

# Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=seu_access_token

# Roblox
ROBLOX_COOKIE=seu_cookie_roblosecurity
ROBLOX_USER_ID=seu_user_id
ROBLOX_UNIVERSE_ID=universe_id_do_seu_jogo
```

### Configuração do Bot no Discord

1. Crie uma aplicação no [Discord Developer Portal](https://discord.com/developers/applications)
2. Ative as **Privileged Gateway Intents**:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
3. Gere o link de convite com permissão de `Administrator`
4. Convide o bot para seu servidor

## 🚀 Uso

```bash
# Inicie o bot
python main.py
```

### Comandos

#### Comandos de Usuário

| Comando                         | Descrição                     |
| ------------------------------- | ----------------------------- |
| `/perfil`                       | Exibe seu perfil e histórico  |
| `/pedidos`                      | Lista seus pedidos            |
| `/preco <quantidade>`           | Calcula preço para quantidade |
| `/verificar_usuario <username>` | Verifica um usuário do Roblox |
| `/ajuda`                        | Exibe informações de ajuda    |

#### Comandos de Administrador

| Comando                            | Descrição                    |
| ---------------------------------- | ---------------------------- |
| `/cupom_criar <código> <desconto>` | Cria cupom de desconto       |
| `/cupom_desativar <código>`        | Desativa um cupom            |
| `/pedido <id>`                     | Consulta detalhes do pedido  |
| `/entregar <id>`                   | Entrega manual               |
| `/reembolsar <id>`                 | Processa reembolso           |
| `/stats`                           | Exibe estatísticas de vendas |
| `/top_compradores`                 | Ranking de compradores       |
| `/setup_painel`                    | Configura painel de vendas   |

### Fluxo de Compra

```
1. Cliente clica em "Comprar Robux" → Ticket criado
2. Cliente informa quantidade + usuário Roblox
3. Pagamento PIX gerado automaticamente
4. Pagamento verificado em tempo real
5. Link do Gamepass disponibilizado
6. Cliente compra o Gamepass → Robux entregues
```

## 🔒 Considerações de Segurança

- **Variáveis de Ambiente** - Todos os segredos armazenados em `.env` (ignorado pelo git)
- **Segurança do Cookie** - Cookie do Roblox nunca é logado ou exposto
- **Validação de Entrada** - Validators do Pydantic para todos os inputs
- **Rate Limiting** - Previne abuso das APIs
- **Método Gamepass** - Utiliza método oficial do Roblox, compatível com ToS

## 📊 Esquema do Banco de Dados

```sql
-- Entidades principais
Users       → Dados do usuário Discord/Roblox, histórico de compras
Orders      → Registros de transações com rastreamento de status
Tickets     → Gerenciamento de tickets de suporte
Coupons     → Códigos de desconto com limites de uso
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir um Pull Request.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Contato

Para dúvidas ou sugestões, abra uma issue ou entre em contato via Discord.

---

<p align="center">
  <sub>Desenvolvido com ❤️ usando Python e discord.py</sub>
</p>
