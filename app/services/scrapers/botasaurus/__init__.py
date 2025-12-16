"""Botasaurus scraper implementation."""
from .scraper import BotasaurusScraper
from .request_queue import RequestQueue, DEFAULT_REQUEST_DELAY

__all__ = ["BotasaurusScraper", "RequestQueue", "DEFAULT_REQUEST_DELAY"]
