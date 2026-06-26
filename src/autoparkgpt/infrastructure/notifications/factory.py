"""Select notifier adapters based on configuration."""

from __future__ import annotations

from autoparkgpt.domain.ports.notifications import AdminNotifierPort, UserNotifierPort
from autoparkgpt.infrastructure.config import AdminSettings
from autoparkgpt.infrastructure.notifications.logging_notifier import (
    LoggingAdminNotifier,
    LoggingUserNotifier,
)
from autoparkgpt.infrastructure.notifications.webhook_notifier import (
    WebhookAdminNotifier,
    WebhookUserNotifier,
)


def build_admin_notifier(settings: AdminSettings) -> AdminNotifierPort:
    """Webhook notifier when an admin URL is configured, otherwise a logging notifier."""

    if settings.admin_webhook_url:
        return WebhookAdminNotifier(settings.admin_webhook_url, settings.notify_timeout_seconds)
    return LoggingAdminNotifier()


def build_user_notifier(settings: AdminSettings) -> UserNotifierPort:
    """Webhook notifier when a user URL is configured, otherwise a logging notifier."""

    if settings.user_webhook_url:
        return WebhookUserNotifier(settings.user_webhook_url, settings.notify_timeout_seconds)
    return LoggingUserNotifier()
