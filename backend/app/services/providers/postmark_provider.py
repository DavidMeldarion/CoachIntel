from app.services.email_service import EmailService, append_unsubscribe_footer
from postmarker.core import PostmarkClient
import logging
import os

class PostmarkProvider(EmailService):
    """
    EmailService implementation using Postmark via the postmarker package.
    """
    def __init__(self, api_key: str):
        """
        Initialize the PostmarkProvider with the given API key.

        Args:
            api_key (str): Postmark server API token.
        """
        self.client = PostmarkClient(server_token=api_key)
        self.logger = logging.getLogger("PostmarkProvider")
        self.from_email = os.getenv("MAIL_FROM", "Casey From CoachIntel <Casey@coachintel.ai>")

    def send(self, to: str, subject: str, html: str, meta: dict | None = None) -> str | None:
        """
        Send an email using Postmark and return message id if available.

        Args:
            to (str): Recipient's email address.
            subject (str): Subject line of the email.
            html (str): HTML body of the email.
            meta (dict | None, optional): Optional metadata. Defaults to None.
        """
        try:
            # Append unsubscribe footer if we have lead_id
            lead_id = None
            if isinstance(meta, dict):
                lead_id = meta.get('lead_id')
            html = append_unsubscribe_footer(html, lead_id)
            self.logger.info(f"Sending email to provider; meta has lead_id={bool(lead_id)}")
            resp = self.client.emails.send(
                From=self.from_email,
                To=to,
                Subject=subject,
                HtmlBody=html
            )
            message_id = None
            try:
                message_id = resp.get('MessageID') if isinstance(resp, dict) else None
            except Exception:
                pass
            self.logger.info(f"Email sent to {to} via Postmark. message_id={message_id}")
            return message_id
        except Exception as e:
            self.logger.error(f"Failed to send email to {to} via Postmark: {e}")
            raise
