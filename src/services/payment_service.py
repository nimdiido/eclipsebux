import mercadopago
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from loguru import logger
from src.config import get_settings


class MercadoPagoService:
    """Serviço de integração com Mercado Pago para pagamentos PIX."""

    def __init__(self):
        settings = get_settings()
        self._sdk = mercadopago.SDK(settings.mercadopago_access_token)
        self._expiration_minutes = settings.pix_expiration_minutes

    async def create_pix_payment(
        self,
        amount: float,
        order_id: str,
        description: str,
        payer_email: str = "cliente@email.com",
        payer_name: str = "Cliente",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Cria um pagamento PIX.

        Returns:
            Tuple[bool, Dict]: (sucesso, dados do pagamento ou erro)
        """
        try:
            expiration = datetime.now(timezone.utc) + timedelta(
                minutes=self._expiration_minutes
            )
            # Formato esperado: yyyy-MM-dd'T'HH:mm:ss.sssZ
            expiration_str = expiration.strftime("%Y-%m-%dT%H:%M:%S.000-00:00")

            payment_data = {
                "transaction_amount": float(amount),
                "description": description,
                "payment_method_id": "pix",
                "payer": {
                    "email": payer_email,
                    "first_name": payer_name.split()[0] if payer_name else "Cliente",
                    "last_name": (
                        payer_name.split()[-1] if len(payer_name.split()) > 1 else ""
                    ),
                },
                "date_of_expiration": expiration_str,
                "external_reference": order_id,
                "notification_url": None,  # Configure se tiver webhook
            }

            # Executa em thread separada (SDK é síncrono)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self._sdk.payment().create(payment_data)
            )

            if response["status"] == 201:
                payment = response["response"]

                # Extrai dados do PIX
                pix_data = payment.get("point_of_interaction", {}).get(
                    "transaction_data", {}
                )

                result = {
                    "payment_id": str(payment["id"]),
                    "status": payment["status"],
                    "pix_code": pix_data.get("qr_code", ""),
                    "pix_qrcode_base64": pix_data.get("qr_code_base64", ""),
                    "pix_ticket_url": pix_data.get("ticket_url", ""),
                    "amount": payment["transaction_amount"],
                    "expires_at": expiration,
                    "external_reference": order_id,
                }

                logger.success(
                    f"💳 Pagamento PIX criado: {payment['id']} - R${amount:.2f}"
                )
                return True, result
            else:
                error = response.get("response", {})
                logger.error(f"❌ Erro ao criar PIX: {error}")
                return False, {"error": str(error)}

        except Exception as e:
            logger.error(f"❌ Exceção ao criar PIX: {e}")
            return False, {"error": str(e)}

    async def check_payment_status(self, payment_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Verifica status de um pagamento.

        Returns:
            Tuple[str, Dict]: (status, dados do pagamento)
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self._sdk.payment().get(payment_id)
            )

            if response["status"] == 200:
                payment = response["response"]
                return payment["status"], payment
            else:
                return "error", response.get("response", {})

        except Exception as e:
            logger.error(f"❌ Erro ao verificar pagamento: {e}")
            return "error", {"error": str(e)}

    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancela um pagamento pendente."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._sdk.payment().update(payment_id, {"status": "cancelled"}),
            )

            success = response["status"] == 200
            if success:
                logger.info(f"🚫 Pagamento cancelado: {payment_id}")
            return success

        except Exception as e:
            logger.error(f"❌ Erro ao cancelar pagamento: {e}")
            return False

    async def refund_payment(
        self, payment_id: str, amount: Optional[float] = None
    ) -> Tuple[bool, Dict]:
        """
        Reembolsa um pagamento.

        Args:
            payment_id: ID do pagamento
            amount: Valor a reembolsar (None = total)
        """
        try:
            refund_data = {}
            if amount:
                refund_data["amount"] = amount

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self._sdk.refund().create(payment_id, refund_data)
            )

            if response["status"] == 201:
                logger.success(f"💰 Reembolso criado para pagamento: {payment_id}")
                return True, response["response"]
            else:
                return False, response.get("response", {})

        except Exception as e:
            logger.error(f"❌ Erro ao reembolsar: {e}")
            return False, {"error": str(e)}


class PaymentChecker:
    """Verificador de pagamentos em background."""

    def __init__(self, mp_service: MercadoPagoService, callback):
        self._mp = mp_service
        self._callback = callback  # Função a chamar quando pagamento for confirmado
        self._running = False
        self._pending_payments: Dict[str, str] = {}  # payment_id -> order_id

    def add_payment(self, payment_id: str, order_id: str) -> None:
        """Adiciona pagamento para monitorar."""
        self._pending_payments[payment_id] = order_id
        logger.debug(f"👀 Monitorando pagamento: {payment_id}")

    def remove_payment(self, payment_id: str) -> None:
        """Remove pagamento do monitoramento."""
        self._pending_payments.pop(payment_id, None)

    async def start(self) -> None:
        """Inicia o verificador em background."""
        self._running = True
        logger.info("🔄 Iniciando verificador de pagamentos...")

        while self._running:
            try:
                # Copia para evitar modificação durante iteração
                payments = dict(self._pending_payments)

                for payment_id, order_id in payments.items():
                    status, data = await self._mp.check_payment_status(payment_id)

                    if status == "approved":
                        logger.success(f"✅ Pagamento aprovado: {payment_id}")
                        self.remove_payment(payment_id)

                        if self._callback:
                            await self._callback(order_id, payment_id, data)

                    elif status in ["cancelled", "rejected", "refunded"]:
                        logger.warning(f"❌ Pagamento {status}: {payment_id}")
                        self.remove_payment(payment_id)

                    # Rate limit
                    await asyncio.sleep(0.5)

                # Verifica a cada 10 segundos
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"❌ Erro no verificador: {e}")
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Para o verificador."""
        self._running = False
        logger.info("⏹️ Verificador de pagamentos parado")


# Instância global do serviço
mercadopago_service = MercadoPagoService()
