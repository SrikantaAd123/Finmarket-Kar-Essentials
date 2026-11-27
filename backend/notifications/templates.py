
"""
Email templates for Finmarket Kart Essentials.

Provides reusable HTML and plain-text notification content.

Supported notification types:
- order_confirmation
- order_status
- payment_success
- payment_failed
- refund_update
- shipment_update
- delivery_update
- account_update
- promotional
- general

All dynamic values are HTML-escaped before being inserted
into email content.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class EmailContent:
    """Rendered email content."""

    subject: str
    html_body: str
    text_body: str


# =========================================================
# TEMPLATE DEFINITIONS
# =========================================================

TEMPLATE_TITLES: dict[str, str] = {
    "order_confirmation": "Your order is confirmed",
    "order_status": "Your order has been updated",
    "payment_success": "Payment successful",
    "payment_failed": "Payment unsuccessful",
    "refund_update": "Refund update",
    "shipment_update": "Shipment update",
    "delivery_update": "Delivery update",
    "account_update": "Account update",
    "promotional": "A special update for you",
    "general": "Notification from Finmarket Kart",
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _clean_text(value: Any) -> str:
    """Convert a value to safe, readable plain text."""

    if value is None:
        return ""

    return str(value).strip()


def _escape_html(value: Any) -> str:
    """Escape dynamic content before inserting it into HTML."""

    return escape(_clean_text(value))


def _format_context(
    context: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Convert template context values into safe strings."""

    if not context:
        return {}

    return {
        str(key): _clean_text(value)
        for key, value in context.items()
        if value is not None
    }


# =========================================================
# PLAIN-TEXT TEMPLATE
# =========================================================

def render_text_template(
    subject: str,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> str:
    """Render a plain-text notification email."""

    values = _format_context(context)

    lines = [
        "FINMARKET KART",
        "=" * 40,
        "",
        subject,
        "",
        message,
    ]

    if values:
        lines.extend(["", "Additional details:"])

        for key, value in values.items():
            lines.append(f"{key.replace('_', ' ').title()}: {value}")

    lines.extend(
        [
            "",
            "-" * 40,
            "Thank you for choosing Finmarket Kart.",
            "This is an automated notification.",
        ]
    )

    return "\n".join(lines)


# =========================================================
# HTML TEMPLATE
# =========================================================

def render_html_template(
    subject: str,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> str:
    """Render a responsive HTML notification email."""

    safe_subject = _escape_html(subject)

    # Escape message content and preserve its line breaks.
    safe_message = _escape_html(message).replace(
        "\n",
        "<br>",
    )

    values = _format_context(context)

    details_html = ""

    if values:
        rows = []

        for key, value in values.items():
            safe_key = _escape_html(
                key.replace("_", " ").title()
            )
            safe_value = _escape_html(value)

            rows.append(
                f"""
                <tr>
                    <td style="
                        padding: 10px;
                        border-bottom: 1px solid #eeeeee;
                        color: #666666;
                        font-weight: 600;
                    ">
                        {safe_key}
                    </td>
                    <td style="
                        padding: 10px;
                        border-bottom: 1px solid #eeeeee;
                        color: #222222;
                    ">
                        {safe_value}
                    </td>
                </tr>
                """
            )

        details_html = f"""
        <table role="presentation" width="100%"
               cellspacing="0" cellpadding="0"
               style="border-collapse: collapse; margin-top: 20px;">
            {''.join(rows)}
        </table>
        """

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_subject}</title>
</head>
<body style="
    margin: 0;
    padding: 0;
    background-color: #f4f5f7;
    font-family: Arial, Helvetica, sans-serif;
">
    <table role="presentation" width="100%"
           cellspacing="0" cellpadding="0"
           style="background-color: #f4f5f7; padding: 30px 12px;">
        <tr>
            <td align="center">
                <table role="presentation" width="600"
                       cellspacing="0" cellpadding="0"
                       style="
                           max-width: 600px;
                           width: 100%;
                           background-color: #ffffff;
                           border-radius: 10px;
                           overflow: hidden;
                       ">
                    <tr>
                        <td style="
                            background-color: #173f35;
                            padding: 24px;
                            color: #ffffff;
                            text-align: center;
                        ">
                            <h1 style="
                                margin: 0;
                                font-size: 24px;
                                letter-spacing: 1px;
                            ">
                                FINMARKET KART
                            </h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="
                                margin-top: 0;
                                color: #222222;
                                font-size: 21px;
                            ">
                                {safe_subject}
                            </h2>

                            <p style="
                                color: #444444;
                                font-size: 15px;
                                line-height: 1.7;
                            ">
                                {safe_message}
                            </p>

                            {details_html}

                            <p style="
                                margin-top: 30px;
                                color: #444444;
                                font-size: 14px;
                            ">
                                Thank you for choosing Finmarket Kart.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="
                            padding: 18px;
                            background-color: #f8f8f8;
                            color: #777777;
                            text-align: center;
                            font-size: 12px;
                        ">
                            This is an automated notification.
                            Please do not reply to this email.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


# =========================================================
# MAIN TEMPLATE RENDERER
# =========================================================

def render_notification_template(
    template_name: str | None,
    context: Mapping[str, Any] | None = None,
    subject: str | None = None,
    message: str | None = None,
) -> EmailContent:
    """
    Render a notification using a named template.

    Unknown or missing template names use the general template.

    Args:
        template_name: Notification template identifier.
        context: Optional dynamic notification values.
        subject: Optional subject override.
        message: Notification message.

    Returns:
        EmailContent containing subject, HTML and plain text.
    """

    normalized_name = (
        (template_name or "general").strip().lower()
    )

    default_subject = TEMPLATE_TITLES.get(
        normalized_name,
        TEMPLATE_TITLES["general"],
    )

    final_subject = (
        _clean_text(subject)
        or default_subject
    )

    final_message = (
        _clean_text(message)
        or "You have a new notification from Finmarket Kart."
    )

    html_body = render_html_template(
        subject=final_subject,
        message=final_message,
        context=context,
    )

    text_body = render_text_template(
        subject=final_subject,
        message=final_message,
        context=context,
    )

    return EmailContent(
        subject=final_subject,
        html_body=html_body,
        text_body=text_body,
    )


__all__ = [
    "EmailContent",
    "TEMPLATE_TITLES",
    "render_text_template",
    "render_html_template",
    "render_notification_template",
]
