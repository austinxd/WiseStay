from __future__ import annotations

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Integration with WhatsApp Business Cloud API."""

    @staticmethod
    def _get_base_url() -> str:
        api_url = getattr(settings, "WHATSAPP_API_URL", "https://graph.facebook.com/v18.0")
        phone_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        return f"{api_url}/{phone_id}"

    @staticmethod
    def _get_headers() -> dict:
        token = getattr(settings, "WHATSAPP_API_TOKEN", "")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def send_message(to_phone: str, message: str) -> dict | None:
        url = f"{WhatsAppService._get_base_url()}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone.replace("+", ""),
            "type": "text",
            "text": {"body": message},
        }
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(url, json=payload, headers=WhatsAppService._get_headers())
                response.raise_for_status()
                data = response.json()
                logger.info("WhatsApp message sent to %s", to_phone)
                return data
        except Exception as exc:
            logger.error("WhatsApp send_message failed to %s: %s", to_phone, exc)
            return None

    @staticmethod
    def send_template_message(
        to_phone: str,
        template_name: str,
        parameters: list[str] = None,
        language_code: str = "en_US",
    ) -> dict | None:
        url = f"{WhatsAppService._get_base_url()}/messages"
        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in parameters],
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone.replace("+", ""),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(url, json=payload, headers=WhatsAppService._get_headers())
                response.raise_for_status()
                data = response.json()
                logger.info("WhatsApp template '%s' sent to %s", template_name, to_phone)
                return data
        except Exception as exc:
            logger.error("WhatsApp template send failed: %s", exc)
            return None

    @staticmethod
    def verify_webhook(mode: str, token: str, challenge: str) -> str | None:
        verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "")
        if mode == "subscribe" and token == verify_token:
            return challenge
        return None

    @staticmethod
    def parse_incoming_message(payload: dict) -> dict | None:
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None
            changes = entry[0].get("changes", [])
            if not changes:
                return None
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            if msg.get("type") != "text":
                return None

            from_phone = msg.get("from", "")
            if from_phone and not from_phone.startswith("+"):
                from_phone = f"+{from_phone}"

            return {
                "from_phone": from_phone,
                "message_id": msg.get("id", ""),
                "text": msg.get("text", {}).get("body", ""),
                "timestamp": msg.get("timestamp", ""),
            }
        except (IndexError, KeyError, TypeError) as exc:
            logger.warning("Failed to parse WhatsApp payload: %s", exc)
            return None
