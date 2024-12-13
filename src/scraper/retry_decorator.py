import asyncio
import logging
import socket
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar('T')


async def switch_proxy():
    """Torの新しい回路を要求"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 9051))
            s.send(b'AUTHENTICATE ""\r\n')
            s.send(b'SIGNAL NEWNYM\r\n')
    except Exception as e:
        print(f"Failed to switch Tor circuit: {e}")

# scraper/retry_decorator.py


def with_retry(
    max_retries: int = 5,
    initial_delay: float = 5.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logging.error(
                        f"Attempt {attempt + 1} failed: {str(e)}",
                        exc_info=True
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)

            raise last_exception
        return wrapper
    return decorator
