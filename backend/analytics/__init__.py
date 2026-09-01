"""ماژول‌های تحلیل: توصیفی، تشخیصی و پیش‌بینی."""

from . import descriptive, diagnostic

HANDLERS: dict = {}
HANDLERS.update(descriptive.HANDLERS)
HANDLERS.update(diagnostic.HANDLERS)
