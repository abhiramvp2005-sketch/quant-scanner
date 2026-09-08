import socket
import aiohttp
import logging

logger = logging.getLogger("AlertEngine")

class TelegramAlertManager:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    async def send_alert(self, message: str):
        if not self.token or "your_actual" in self.token or "YOUR_BOT" in self.token:
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