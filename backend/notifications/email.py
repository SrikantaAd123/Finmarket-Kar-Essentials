
"""
Gmail SMTP email sender for Finmarket Kart Essentials.

Uses environment variables for credentials and sender configuration.

Required environment variables:
    SMTP_USERNAME
    SMTP_PASSWORD
    SMTP_FROM_EMAIL

Optional environment variables:
    SMTP_HOST
    SMTP_PORT
    SMTP_FROM_NAME
    SMTP_USE_TLS
    SMTP_USE_SSL
    SMTP_TIMEOUT

Gmail SMTP normally uses:
    Host: smtp.gmail.com
    Port: 587
    Security: STARTTLS

SMTP_PASSWORD must be a Gmail App Password when using
Gmail with two-step verification.
"""

from __future__ import annotations

import os
import smtplib
import ssl

from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any

from backend.notifications.templates import (
    render_notification_template,
)
from dotenv import load_dotenv

load_dotenv()


# =========================================================
# SMTP CONFIGURATION
# =========================================================

DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_TIMEOUT = 30


# =========================================================
# CONFIGURATION HELPERS
# =========================================================

def _get_bool(
    name: str,
    default: bool,
) -> bool:
    """Read a boolean environment variable."""

    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _get_int(
    name: str,
    default: int,
) -> int:
    """Read and validate an integer environment variable."""

    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable {name} must be an integer."
        ) from exc


def _required_env(name: str) -> str:
    """Read a required environment variable."""

    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


# =========================================================
# SMTP SETTINGS
# =========================================================

def get_smtp_settings() -> dict[str, Any]:
    """
    Load and validate SMTP configuration.

    Credentials are never stored in source code.
    """

    username = _required_env("SMTP_USERNAME")
    password = _required_env("SMTP_PASSWORD")

    from_email = (
        os.getenv("SMTP_FROM_EMAIL", username).strip()
    )

    from_name = os.getenv(
        "SMTP_FROM_NAME",
        "Finmarket Kart",
    ).strip()

    host = os.getenv(
        "SMTP_HOST",
        DEFAULT_SMTP_HOST,
    ).strip()

    port = _get_int(
        "SMTP_PORT",
        DEFAULT_SMTP_PORT,
    )

    timeout = _get_int(
        "SMTP_TIMEOUT",
        DEFAULT_SMTP_TIMEOUT,
    )

    use_tls = _get_bool(
        "SMTP_USE_TLS",
        True,
    )

    use_ssl = _get_bool(
        "SMTP_USE_SSL",
        False,
    )

    if use_tls and use_ssl:
        raise ValueError(
            "SMTP_USE_TLS and SMTP_USE_SSL cannot both be enabled."
        )

    if not 1 <= port <= 65535:
        raise ValueError(
            "SMTP_PORT must be between 1 and 65535."
        )

    if timeout <= 0:
        raise ValueError(
            "SMTP_TIMEOUT must be greater than zero."
        )

    if not host:
        raise ValueError(
            "SMTP_HOST cannot be empty."
        )

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
        "from_name": from_name,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "timeout": timeout,
    }


# =========================================================
# EMAIL MESSAGE BUILDER
# =========================================================

def _build_email_message(
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
    settings: dict[str, Any],
) -> EmailMessage:
    """Build a multipart plain-text and HTML email."""

    recipient = recipient.strip()

    if not recipient or "@" not in recipient:
        raise ValueError(
            "A valid recipient email address is required."
        )

    if not subject.strip():
        raise ValueError(
            "Email subject cannot be empty."
        )

    message = EmailMessage()

    message["Subject"] = subject
    message["From"] = formataddr(
        (
            settings["from_name"],
            settings["from_email"],
        )
    )
    message["To"] = recipient

    # Generate a unique message ID for logging/tracking.
    message_id = make_msgid()
    message["Message-ID"] = message_id

    # Plain-text fallback.
    message.set_content(text_body)

    # HTML alternative.
    message.add_alternative(
        html_body,
        subtype="html",
    )

    return message


# =========================================================
# SMTP DELIVERY
# =========================================================

def _send_message(
    email_message: EmailMessage,
    settings: dict[str, Any],
) -> None:
    """
    Send an email through SMTP.

    Supports:
    - SMTP with STARTTLS.
    - SMTP over SSL.
    """

    context = ssl.create_default_context()

    if settings["use_ssl"]:
        with smtplib.SMTP_SSL(
            host=settings["host"],
            port=settings["port"],
            timeout=settings["timeout"],
            context=context,
        ) as server:
            server.login(
                settings["username"],
                settings["password"],
            )

            server.send_message(email_message)

        return

    with smtplib.SMTP(
        host=settings["host"],
        port=settings["port"],
        timeout=settings["timeout"],
    ) as server:
        server.ehlo()

        if settings["use_tls"]:
            server.starttls(context=context)
            server.ehlo()

        server.login(
            settings["username"],
            settings["password"],
        )

        server.send_message(email_message)


# =========================================================
# PUBLIC EMAIL FUNCTION
# =========================================================

def send_email(
    recipient: str,
    subject: str,
    message: str,
) -> dict[str, str]:
    """
    Send a notification email.

    This is the exact three-argument interface expected by
    NotificationService:

        send_email(recipient, subject, message)

    Returns:
        {
            "provider": "gmail_smtp",
            "message_id": "<generated-message-id>"
        }

    Raises:
        RuntimeError: SMTP configuration or delivery failure.
        ValueError: Invalid recipient or message data.
    """

    if not isinstance(recipient, str):
        raise ValueError(
            "Recipient must be a string."
        )

    if not isinstance(subject, str):
        raise ValueError(
            "Subject must be a string."
        )

    if not isinstance(message, str):
        raise ValueError(
            "Message must be a string."
        )

    try:
        settings = get_smtp_settings()

        content = render_notification_template(
            template_name="general",
            subject=subject,
            message=message,
        )

        email_message = _build_email_message(
            recipient=recipient,
            subject=content.subject,
            text_body=content.text_body,
            html_body=content.html_body,
            settings=settings,
        )

        generated_message_id = email_message["Message-ID"]

        _send_message(
            email_message=email_message,
            settings=settings,
        )

        return {
            "provider": "gmail_smtp",
            "message_id": str(generated_message_id),
        }

    except (ValueError, RuntimeError):
        raise

    except (
        smtplib.SMTPException,
        OSError,
    ) as exc:
        raise RuntimeError(
            f"Email delivery failed: {exc}"
        ) from exc


# =========================================================
# TEMPLATED EMAIL FUNCTION
# =========================================================

def send_templated_email(
    recipient: str,
    template_name: str,
    context: dict[str, Any] | None = None,
    subject: str | None = None,
    message: str | None = None,
) -> dict[str, str]:
    """
    Send an email using a named notification template.

    This function is available for future integration when
    NotificationService passes template_name and template_data.
    """

    if not isinstance(recipient, str):
        raise ValueError(
            "Recipient must be a string."
        )

    try:
        settings = get_smtp_settings()

        content = render_notification_template(
            template_name=template_name,
            context=context,
            subject=subject,
            message=message,
        )

        email_message = _build_email_message(
            recipient=recipient,
            subject=content.subject,
            text_body=content.text_body,
            html_body=content.html_body,
            settings=settings,
        )

        generated_message_id = email_message["Message-ID"]

        _send_message(
            email_message=email_message,
            settings=settings,
        )

        return {
            "provider": "gmail_smtp",
            "message_id": str(generated_message_id),
        }

    except (ValueError, RuntimeError):
        raise

    except (
        smtplib.SMTPException,
        OSError,
    ) as exc:
        raise RuntimeError(
            f"Templated email delivery failed: {exc}"
        ) from exc


__all__ = [
    "get_smtp_settings",
    "send_email",
    "send_templated_email",
]
