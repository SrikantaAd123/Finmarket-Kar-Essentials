
"""
Notification package for Finmarket Kart Essentials.

Provides:
- Gmail SMTP email delivery.
- Reusable notification email templates.
"""

from backend.notifications.email import (
    get_smtp_settings,
    send_email,
    send_templated_email,
)

from backend.notifications.templates import (
    EmailContent,
    TEMPLATE_TITLES,
    render_html_template,
    render_notification_template,
    render_text_template,
)


__all__ = [
    # Email functions
    "get_smtp_settings",
    "send_email",
    "send_templated_email",

    # Template functions
    "EmailContent",
    "TEMPLATE_TITLES",
    "render_html_template",
    "render_notification_template",
    "render_text_template",
]
