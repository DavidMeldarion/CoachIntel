from typing import Optional
import os
from app.utils.crypto import sign_hmac_token

# Base URL for building unsubscribe links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", os.getenv("API_URL", "http://localhost:8000"))


def build_unsubscribe_link(lead_id: str) -> str:
    token = sign_hmac_token(lead_id)
    # Unsubscribe endpoint is served by backend
    return f"{BACKEND_URL}/unsubscribe?lead_id={lead_id}&token={token}"


def append_unsubscribe_footer(html: str, lead_id: Optional[str]) -> str:
    """Append an industry-standard unsubscribe footer to HTML emails.
    If lead_id is provided, includes one-click unsubscribe link.
    """
    footer = ""
    if lead_id:
        link = build_unsubscribe_link(lead_id)
        footer = f"""
        <hr style=\"border:none;border-top:1px solid #eee;margin:24px 0;\"/>
        <p style=\"font-size:12px;color:#6b7280;\">
          You are receiving this email because you signed up for updates from CoachIntel.
          If you no longer wish to receive these emails, you can <a href=\"{link}\">unsubscribe</a> at any time.
        </p>
        """
    else:
        footer = """
        <hr style=\"border:none;border-top:1px solid #eee;margin:24px 0;\"/>
        <p style=\"font-size:12px;color:#6b7280;\">
          You are receiving this email from CoachIntel. To stop receiving these emails, unsubscribe using the link provided in your account.
        </p>
        """

    # Insert footer before closing body/html if present
    if "</body>" in html:
        return html.replace("</body>", footer + "</body>")
    if "</html>" in html:
        return html.replace("</html>", footer + "</html>")
    return html + footer


class EmailService:
    """
    Provider-agnostic email sender interface.
    Subclasses should implement the send method for specific email providers.
    """

    def send(self, to: str, subject: str, html: str, meta: dict | None = None) -> str | None:
        """
        Send an email message.

        Args:
            to (str): Recipient email address.
            subject (str): Subject line.
            html (str): HTML body.
            meta (dict | None): Optional metadata (e.g., lead_id, org_id, template, etc.).
        Returns:
            Optional[str]: Provider-specific message id if available.
        """
        raise NotImplementedError("EmailService.send() must be implemented by a provider-specific subclass.")

def build_summary_email_html(summary: str, action_items: list[str], progress_notes: str, lead_id: Optional[str] = None) -> str:
    """
    Build a styled HTML email body for the meeting summary email.
    """
    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; background: #f8fafc; color: #222; }}
        .container {{ background: #fff; border-radius: 8px; max-width: 600px; margin: 32px auto; padding: 32px; box-shadow: 0 2px 8px #e0e7ef; }}
        h2 {{ color: #2563eb; margin-top: 0; }}
        h3 {{ color: #0e7490; margin-bottom: 8px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 6px; }}
        .footer {{ margin-top: 32px; font-size: 13px; color: #888; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>📝 Your Meeting Summary</h2>
        <p>{summary}</p>
        <h3>✅ Action Items</h3>
        <ul>
          {''.join(f'<li>{item}</li>' for item in action_items) if action_items else '<li>No action items.</li>'}
        </ul>
        <h3>📈 Progress Notes</h3>
        <p>{progress_notes or 'No progress notes.'}</p>
      </div>
    </body>
    </html>
    """
    return append_unsubscribe_footer(html, lead_id)

def send_summary_email(to_email: str, summary: str, action_items: list[str], progress_notes: str, lead_id: Optional[str] = None) -> None:
    """
    Send a summary email to the user with summary, action items, and progress notes.

    Args:
        to_email (str): Recipient's email address.
        summary (str): The main summary text.
        action_items (list[str]): List of action items.
        progress_notes (str): Progress notes text.
    """
    from app.services.factory import get_email_service  # Import locally to avoid circular import
    email_service = get_email_service()
    subject = "Your Meeting Summary"
    html_body = build_summary_email_html(summary, action_items, progress_notes, lead_id=lead_id)
    # Meta can include contextual identifiers; leave None here
    email_service.send(to_email, subject, html_body, meta=None)
