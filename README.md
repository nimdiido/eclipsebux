# 🎮 Bot de Vendas de Robux para Discord

Bot profissional para vendas de Robux via Discord com integração PIX (Mercado Pago) e entrega via Gamepasses.

## 📋 Funcionalidades

- ✅ Sistema de Tickets/Carrinhos
- ✅ Pagamento via PIX automático (Mercado Pago)
- ✅ Verificação automática de pagamentos
- ✅ Sistema de Cupons de desconto
- ✅ Logs completos de transações
- ✅ Comandos administrativos
- ✅ Entrega via Gamepasses (método seguro do Roblox)
- ✅ Interface com botões e modais (Discord Components V2)

## 🚀 Instalação

### 1. Pré-requisitos

- Python 3.10+
- MongoDB
- Conta de desenvolvedor Discord
- Conta Mercado Pago
- Conta Roblox com jogo publicado

### 2. Configuração do Ambiente

```powershell
# Clone o repositório
cd c:\dev\bot\robux

# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente virtual
.\venv\Scripts\Activate.ps1

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configuração

1. Copie o arquivo de exemplo:

```powershell
Copy-Item .env.example .env
```

2. Edite o `.env` com suas credenciais:

- **DISCORD_TOKEN**: Token do bot Discord
- **DISCORD_GUILD_ID**: ID do seu servidor
- **MERCADOPAGO_ACCESS_TOKEN**: Token do Mercado Pago
- **ROBLOX_COOKIE**: Cookie .ROBLOSECURITY da sua conta
- **MONGODB_URI**: URI do MongoDB

### 4. Configuração do Discord

1. Crie um bot no [Discord Developer Portal](https://discord.com/developers/applications)
2. Ative as Intents: `Message Content`, `Server Members`, `Guilds`
3. Convide o bot com permissões de `Administrator`

### 5. Configuração do Mercado Pago

1. Crie uma conta no [Mercado Pago Developers](https://www.mercadopago.com.br/developers)
2. Obtenha o Access Token de produção
3. Configure o webhook (opcional, para confirmação instantânea)

### 6. Configuração do Roblox

1. Tenha um jogo publicado no Roblox
2. Obtenha o Universe ID do jogo
3. Obtenha o cookie .ROBLOSECURITY (DevTools > Application > Cookies)

### 7. Executar

```powershell
# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# Iniciar o bot
python main.py
```

## 📁 Estrutura do Projeto

```
robux/
├── main.py                 # Arquivo principal
├── requirements.txt        # Dependências
├── .env.example           # Exemplo de configuração
├── .env                   # Suas configurações (não committar!)
├── .gitignore
├── README.md
├── logs/                  # Logs do bot
└── src/
    ├── __init__.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py    # Configurações centralizadas
    ├── database/
    │   ├── __init__.py
    │   ├── connection.py  # Conexão MongoDB
    │   ├── models.py      # Modelos de dados
    │   └── repositories.py # Operações do banco
    ├── services/
    │   ├── __init__.py
    │   ├── payment_service.py  # Mercado Pago
    │   └── roblox_service.py   # API do Roblox
    └── cogs/
        ├── __init__.py
        ├── tickets.py     # Sistema de tickets
        ├── orders.py      # Gestão de pedidos
        ├── admin.py       # Comandos admin
        └── user.py        # Comandos de usuário
```

## 🔧 Comandos

### Usuários

| Comando                         | Descrição               |
| ------------------------------- | ----------------------- |
| `/perfil`                       | Mostra seu perfil       |
| `/pedidos`                      | Lista seus pedidos      |
| `/preco <quantidade>`           | Calcula preço           |
| `/verificar_usuario <username>` | Verifica usuário Roblox |
| `/ajuda`                        | Mostra ajuda            |

### Administradores

| Comando                            | Descrição                  |
| ---------------------------------- | -------------------------- |
| `/cupom_criar <código> <desconto>` | Cria cupom                 |
| `/cupom_desativar <código>`        | Desativa cupom             |
| `/pedido <id>`                     | Consulta pedido            |
| `/entregar <id>`                   | Entrega manual             |
| `/reembolsar <id>`                 | Reembolsa pedido           |
| `/stats`                           | Estatísticas               |
| `/top_compradores`                 | Ranking de compradores     |
| `/anunciar <mensagem>`             | Envia anúncio              |
| `/setup_painel`                    | Configura painel de vendas |

## 💳 Fluxo de Compra

1. **Cliente clica em "Comprar Robux"** no canal de vendas
2. **Ticket é criado** automaticamente
3. **Cliente informa** quantidade de Robux e usuário Roblox
4. **PIX é gerado** automaticamente
5. **Pagamento é verificado** em tempo real
6. **Gamepass é disponibilizado** para o cliente comprar
7. **Robux são creditados** na conta do cliente

## 🔒 Segurança

- Método de entrega via Gamepass é 100% permitido pelo Roblox
- Nenhuma senha ou cookie do cliente é solicitado
- Pagamentos verificados automaticamente via API do Mercado Pago
- Logs completos de todas as transações

## ⚠️ Avisos Importantes

1. **Nunca compartilhe** seu cookie .ROBLOSECURITY
2. **Use uma conta secundária** do Roblox para as vendas
3. **Mantenha o MongoDB** seguro e com backup
4. **Monitore os logs** regularmente

## 📞 Suporte

Para dúvidas ou problemas, abra uma issue ou entre em contato.

---

Desenvolvido com ❤️ usando Python e discord.py
