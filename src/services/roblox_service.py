import aiohttp
import asyncio
import re
from typing import Optional, Dict, Any, Tuple, List
from loguru import logger
from aiolimiter import AsyncLimiter
from src.config import get_settings


class RobloxAPI:
    """
    Cliente da API do Roblox.

    Usa a API oficial do Roblox para:
    - Buscar informações de usuários
    - Verificar gamepasses
    - Verificar compras de gamepasses
    """

    BASE_URLS = {
        "users": "https://users.roblox.com",
        "games": "https://games.roblox.com",
        "economy": "https://economy.roblox.com",
        "catalog": "https://catalog.roblox.com",
        "inventory": "https://inventory.roblox.com",
        "apis": "https://apis.roblox.com",
        "www": "https://www.roblox.com",
    }

    def __init__(self):
        self._settings = get_settings()
        self._session: Optional[aiohttp.ClientSession] = None
        # Rate limiter: 60 requests por minuto
        self._limiter = AsyncLimiter(60, 60)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP reutilizável."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                cookies={".ROBLOSECURITY": self._settings.roblox_cookie},
            )
        return self._session

    async def close(self) -> None:
        """Fecha a sessão HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, url: str, **kwargs) -> Tuple[bool, Any]:
        """Faz uma requisição com rate limiting."""
        async with self._limiter:
            try:
                session = await self._get_session()
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return True, await response.json()
                    elif response.status == 429:
                        logger.warning("⚠️ Rate limited pelo Roblox, aguardando...")
                        await asyncio.sleep(30)
                        return await self._request(method, url, **kwargs)
                    else:
                        text = await response.text()
                        return False, {"status": response.status, "error": text}
            except Exception as e:
                logger.error(f"❌ Erro na requisição Roblox: {e}")
                return False, {"error": str(e)}

    # ==================== USUÁRIOS ====================

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Busca usuário pelo username.

        Returns:
            Dict com id, name, displayName ou None se não encontrado
        """
        url = f"{self.BASE_URLS['users']}/v1/usernames/users"
        payload = {"usernames": [username], "excludeBannedUsers": True}

        success, data = await self._request("POST", url, json=payload)

        if success and data.get("data"):
            user = data["data"][0]
            return {
                "id": user["id"],
                "name": user["name"],
                "displayName": user.get("displayName", user["name"]),
            }
        return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Busca usuário pelo ID."""
        url = f"{self.BASE_URLS['users']}/v1/users/{user_id}"
        success, data = await self._request("GET", url)

        if success:
            return {
                "id": data["id"],
                "name": data["name"],
                "displayName": data.get("displayName", data["name"]),
                "created": data.get("created"),
                "isBanned": data.get("isBanned", False),
            }
        return None

    async def validate_username(self, username: str) -> Tuple[bool, Optional[int], str]:
        """
        Valida se um username existe.

        Returns:
            Tuple[bool, Optional[int], str]: (válido, user_id, mensagem)
        """
        user = await self.get_user_by_username(username)

        if user:
            if user.get("isBanned"):
                return False, None, "Usuário banido"
            return True, user["id"], f"Usuário válido: {user['displayName']}"
        return False, None, "Usuário não encontrado"

    # ==================== GAMEPASSES ====================

    async def get_gamepass_info(self, gamepass_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca informações de um gamepass.
        """
        url = f"{self.BASE_URLS['economy']}/v1/game-pass/{gamepass_id}/game-pass-product-info"
        success, data = await self._request("GET", url)

        if success:
            return {
                "id": data.get("TargetId"),
                "name": data.get("Name"),
                "price": data.get("PriceInRobux"),
                "creator_id": data.get("Creator", {}).get("Id"),
                "is_for_sale": data.get("IsForSale", False),
            }
        return None

    async def get_universe_gamepasses(self, universe_id: int) -> List[Dict[str, Any]]:
        """
        Lista gamepasses de um universe (jogo).
        """
        url = f"{self.BASE_URLS['games']}/v1/games/{universe_id}/game-passes"
        params = {"limit": 100, "sortOrder": "Desc"}

        success, data = await self._request("GET", url, params=params)

        if success:
            return [
                {
                    "id": gp["id"],
                    "name": gp["name"],
                    "price": gp.get("price"),
                    "is_for_sale": gp.get("isForSale", False),
                }
                for gp in data.get("data", [])
            ]
        return []

    async def check_user_owns_gamepass(self, user_id: int, gamepass_id: int) -> bool:
        """
        Verifica se usuário possui um gamepass.
        """
        url = f"{self.BASE_URLS['inventory']}/v1/users/{user_id}/items/GamePass/{gamepass_id}"
        success, data = await self._request("GET", url)

        if success:
            return len(data.get("data", [])) > 0
        return False

    async def wait_for_gamepass_purchase(
        self,
        user_id: int,
        gamepass_id: int,
        timeout_seconds: int = 300,
        check_interval: int = 10,
    ) -> bool:
        """
        Aguarda usuário comprar um gamepass.

        Args:
            user_id: ID do usuário
            gamepass_id: ID do gamepass
            timeout_seconds: Tempo máximo de espera
            check_interval: Intervalo entre verificações

        Returns:
            bool: True se usuário comprou, False se timeout
        """
        elapsed = 0

        while elapsed < timeout_seconds:
            if await self.check_user_owns_gamepass(user_id, gamepass_id):
                logger.success(f"✅ Usuário {user_id} comprou gamepass {gamepass_id}")
                return True

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        logger.warning(f"⏰ Timeout aguardando compra do gamepass {gamepass_id}")
        return False

    # ==================== AUTENTICAÇÃO ====================

    async def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Retorna informações do usuário autenticado (pelo cookie)."""
        url = f"{self.BASE_URLS['users']}/v1/users/authenticated"
        success, data = await self._request("GET", url)

        if success:
            return data
        return None

    async def validate_cookie(self) -> Tuple[bool, str]:
        """
        Valida se o cookie .ROBLOSECURITY está funcionando.

        Returns:
            Tuple[bool, str]: (válido, mensagem)
        """
        user = await self.get_authenticated_user()

        if user:
            return True, f"Autenticado como: {user.get('name')} (ID: {user.get('id')})"
        return False, "Cookie inválido ou expirado"

    # ==================== UTILIDADES ====================

    def generate_gamepass_url(self, gamepass_id: int) -> str:
        """Gera URL de um gamepass."""
        return f"https://www.roblox.com/game-pass/{gamepass_id}"

    def parse_gamepass_url(self, url: str) -> Optional[int]:
        """
        Extrai ID do gamepass de uma URL.

        Suporta formatos:
        - https://www.roblox.com/game-pass/123456
        - https://roblox.com/game-pass/123456/name
        """
        patterns = [
            r"roblox\.com/game-pass/(\d+)",
            r"gamepass/(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(1))
        return None

    # ==================== COMPRA DE GAMEPASS ====================

    async def _get_csrf_token(self) -> Optional[str]:
        """
        Obtém o X-CSRF-Token necessário para requisições POST.
        O Roblox retorna o token no header de uma requisição falhada.
        """
        try:
            session = await self._get_session()
            url = f"{self.BASE_URLS['economy']}/v1/purchases/products/0"

            async with session.post(url) as response:
                csrf_token = response.headers.get("x-csrf-token")
                if csrf_token:
                    logger.debug(f"🔑 CSRF Token obtido: {csrf_token[:20]}...")
                    return csrf_token

        except Exception as e:
            logger.error(f"❌ Erro ao obter CSRF token: {e}")

        return None

    async def _get_gamepass_product_id(self, gamepass_id: int) -> Optional[int]:
        """
        Obtém o Product ID do gamepass (necessário para compra).
        """
        url = f"{self.BASE_URLS['economy']}/v1/game-pass/{gamepass_id}/game-pass-product-info"
        success, data = await self._request("GET", url)

        if success:
            return data.get("ProductId")
        return None

    async def validate_gamepass_for_purchase(
        self, gamepass_id: int, expected_price: int, expected_owner_id: int
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida se um gamepass está correto para compra.

        Args:
            gamepass_id: ID do gamepass
            expected_price: Preço esperado em Robux
            expected_owner_id: ID do dono esperado (cliente)

        Returns:
            Tuple[bool, str, Dict]: (válido, mensagem, info do gamepass)
        """
        info = await self.get_gamepass_info(gamepass_id)

        if not info:
            return False, "❌ Gamepass não encontrado ou não existe.", None

        # Verifica se está à venda
        if not info.get("is_for_sale"):
            return False, "❌ Gamepass não está à venda. Ative a venda no Roblox.", None

        # Verifica preço
        actual_price = info.get("price")
        if actual_price is None:
            return False, "❌ Gamepass não tem preço definido.", None

        # Tolerância de 5 Robux para arredondamentos
        if abs(actual_price - expected_price) > 5:
            return (
                False,
                f"❌ Preço incorreto! Esperado: {expected_price} R$, Atual: {actual_price} R$",
                None,
            )

        # Verifica dono
        if info.get("creator_id") != expected_owner_id:
            return (
                False,
                f"❌ Gamepass não pertence ao usuário correto. Dono atual: {info.get('creator_id')}",
                None,
            )

        return True, "✅ Gamepass validado com sucesso!", info

    async def purchase_gamepass(self, gamepass_id: int) -> Tuple[bool, str]:
        """
        Compra um gamepass automaticamente.

        Args:
            gamepass_id: ID do gamepass a comprar

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # 1. Busca informações do gamepass
            info = await self.get_gamepass_info(gamepass_id)
            if not info:
                return False, "❌ Gamepass não encontrado."

            if not info.get("is_for_sale"):
                return False, "❌ Gamepass não está à venda."

            price = info.get("price", 0)
            seller_id = info.get("creator_id")

            # 2. Obtém Product ID
            product_id = await self._get_gamepass_product_id(gamepass_id)
            if not product_id:
                return False, "❌ Não foi possível obter Product ID do gamepass."

            # 3. Obtém CSRF Token
            csrf_token = await self._get_csrf_token()
            if not csrf_token:
                return False, "❌ Não foi possível obter token de autenticação."

            # 4. Faz a compra
            session = await self._get_session()
            url = f"{self.BASE_URLS['economy']}/v1/purchases/products/{product_id}"

            purchase_data = {
                "expectedCurrency": 1,  # 1 = Robux
                "expectedPrice": price,
                "expectedSellerId": seller_id,
            }

            headers = {"x-csrf-token": csrf_token, "Content-Type": "application/json"}

            async with session.post(
                url, json=purchase_data, headers=headers
            ) as response:
                result = await response.json()

                if response.status == 200:
                    if result.get("purchased"):
                        logger.success(
                            f"✅ Gamepass {gamepass_id} comprado com sucesso! Preço: {price} R$"
                        )
                        return (
                            True,
                            f"✅ Gamepass comprado com sucesso! {price} Robux gastos.",
                        )
                    else:
                        reason = result.get("reason", "Motivo desconhecido")
                        return False, f"❌ Compra falhou: {reason}"

                elif response.status == 403:
                    # Pode precisar de novo CSRF token
                    new_csrf = response.headers.get("x-csrf-token")
                    if new_csrf:
                        # Tenta novamente com novo token
                        headers["x-csrf-token"] = new_csrf
                        async with session.post(
                            url, json=purchase_data, headers=headers
                        ) as retry_response:
                            retry_result = await retry_response.json()
                            if retry_response.status == 200 and retry_result.get(
                                "purchased"
                            ):
                                logger.success(
                                    f"✅ Gamepass {gamepass_id} comprado com sucesso (retry)!"
                                )
                                return (
                                    True,
                                    f"✅ Gamepass comprado com sucesso! {price} Robux gastos.",
                                )

                    error_msg = result.get(
                        "message",
                        result.get("errors", [{}])[0].get("message", "Acesso negado"),
                    )
                    return False, f"❌ Erro de autenticação: {error_msg}"

                elif response.status == 400:
                    error_msg = result.get("message", "Requisição inválida")
                    return False, f"❌ Erro: {error_msg}"

                else:
                    return False, f"❌ Erro inesperado (status {response.status})"

        except Exception as e:
            logger.error(f"❌ Exceção ao comprar gamepass: {e}")
            return False, f"❌ Erro interno: {str(e)}"

    async def get_my_robux_balance(self) -> Optional[int]:
        """
        Retorna o saldo de Robux da conta autenticada.
        """
        try:
            user = await self.get_authenticated_user()
            if not user:
                return None

            user_id = user.get("id")
            url = f"{self.BASE_URLS['economy']}/v1/users/{user_id}/currency"

            success, data = await self._request("GET", url)

            if success:
                return data.get("robux", 0)

        except Exception as e:
            logger.error(f"❌ Erro ao buscar saldo de Robux: {e}")

        return None

    async def full_purchase_flow(
        self, gamepass_id: int, expected_price: int, expected_owner_id: int
    ) -> Tuple[bool, str]:
        """
        Fluxo completo de validação e compra de gamepass.

        Args:
            gamepass_id: ID do gamepass
            expected_price: Preço esperado
            expected_owner_id: ID do dono (cliente)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem detalhada)
        """
        # 1. Verifica saldo
        balance = await self.get_my_robux_balance()
        if balance is None:
            return (
                False,
                "❌ Não foi possível verificar saldo de Robux. Cookie pode estar inválido.",
            )

        if balance < expected_price:
            return (
                False,
                f"❌ Saldo insuficiente! Disponível: {balance} R$, Necessário: {expected_price} R$",
            )

        logger.info(
            f"💰 Saldo atual: {balance} R$, Preço do gamepass: {expected_price} R$"
        )

        # 2. Valida gamepass
        valid, msg, info = await self.validate_gamepass_for_purchase(
            gamepass_id, expected_price, expected_owner_id
        )

        if not valid:
            return False, msg

        logger.info(f"✅ Gamepass validado: {info.get('name')} - {expected_price} R$")

        # 3. Compra
        success, purchase_msg = await self.purchase_gamepass(gamepass_id)

        return success, purchase_msg


# Instância global
roblox_api = RobloxAPI()
