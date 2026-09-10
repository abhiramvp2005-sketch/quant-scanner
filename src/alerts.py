import json
import logging
import socket
import urllib.request
import aiohttp

logger = logging.getLogger("AlertEngine")

class TelegramAlertManager:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def is_configured(self) -> bool:
        return bool(self.token and "your_actual" not in self.token and "YOUR_BOT" not in self.token and "YOUR_CHAT_ID" not in self.chat_id)

    async def send_alert(self, message: str):
        if not self.is_configured():
            logger.warning(f"Telegram execution skipped. Bot credentials not configured. Logged: {message}")
            return
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            connector = aiohttp.TCPConnector(family=socket.AF_INET, resolver=aiohttp.ThreadedResolver())
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Telegram alert broadcast successfully pushed.")
                    else:
                        raw_err = await response.text()
                        logger.error(f"Telegram network API rejection code {response.status}: {raw_err}")
        except Exception as e:
            logger.error(f"Failed to transmit infrastructure alert over network layers: {str(e)}")

    def send_alert_sync(self, message: str):
        if not self.is_configured():
            logger.warning(f"Telegram execution skipped. Bot credentials not configured. Logged: {message}")
            return
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info("Telegram alert broadcast successfully pushed.")
                else:
                    logger.error(f"Telegram network API rejection code {response.status}")
        except Exception as e:
            logger.error(f"Failed to transmit infrastructure alert over network layers: {str(e)}")