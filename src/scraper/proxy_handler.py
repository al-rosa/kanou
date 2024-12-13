# scraper/proxy_handler.py
import asyncio
import logging
import socket
from typing import Optional


class TorProxyHandler:
    def __init__(self, control_port: int = 9051, proxy_port: int = 9050):
        self.control_port = control_port
        self.proxy_port = proxy_port
        self.logger = logging.getLogger(__name__)

    async def new_identity(self) -> bool:
        """Torの新しいIDを要求（新しいIP取得）"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', self.control_port))
                s.send(b'AUTHENTICATE ""\r\n')
                s.send(b'SIGNAL NEWNYM\r\n')
                self.logger.info("Requested new Tor identity")
                await asyncio.sleep(5)  # 新しい回路の確立を待機
                return True
        except Exception as e:
            self.logger.error(f"Failed to get new Tor identity: {e}")
            return False

    def get_proxy_url(self) -> str:
        """プロキシURLを取得"""
        return f"socks5://127.0.0.1:{self.proxy_port}"
