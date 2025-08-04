class EmailService:
    """
    Provider-agnostic email sender interface.
    Subclasses should implement the send method for specific email providers.
    """

    def send(self, to_email: str, subject: str, body: str) -> None:
        """
        Send an email message.

        Args:
            to_email (str): Recipient's email address.
            subject (str): Subject line of the email.
            body (str): Plain text or HTML body of the email.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("EmailService.send() must be implemented by a provider-specific subclass.")

def build_summary_email_html(summary: str, action_items: list[str], progress_notes: str) -> str:
    """
    Build a styled HTML email body for the meeting summary email.
    """
    return f"""
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
        <div class="footer">
          <hr style="border:none;border-top:1px solid #eee;margin:24px 0;"/>
          <div>Sent by CoachSync &mdash; AI-powered coaching platform</div>
        </div>
      </div>
    </body>
    </html>
    """

def send_summary_email(to_email: str, summary: str, action_items: list[str], progress_notes: str) -> None:
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
    html_body = build_summary_email_html(summary, action_items, progress_notes)
    email_service.send(to_email, subject, html_body)
