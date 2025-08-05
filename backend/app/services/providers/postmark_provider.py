from app.services.email_service import EmailService
from postmarker.core import PostmarkClient
import logging

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

    def send(self, to_email: str, subject: str, body: str) -> None:
        """
        Send an email using Postmark.

        Args:
            to_email (str): Recipient's email address.
            subject (str): Subject line of the email.
            body (str): Plain text or HTML body of the email.
        """
        try:
            self.logger.info(f"Sending email to {to_email} via Postmark...")
            self.client.emails.send(
                From="Casey From CoachIntel <Casey@coachintel.ai>",
                To=to_email,
                Subject=subject,
                HtmlBody=body
            )
            self.logger.info(f"Email sent to {to_email} via Postmark.")
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email} via Postmark: {e}")
            raise
