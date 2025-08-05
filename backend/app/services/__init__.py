import os
from app.services.providers.postmark_provider import PostmarkProvider

def get_email_service():
    """
    Factory function to get an email service provider instance based on the EMAIL_PROVIDER environment variable.
    Currently supports only 'postmark'.

    Returns:
        EmailService: An instance of a provider-specific EmailService subclass.
    Raises:
        ValueError: If the provider is unsupported or required env vars are missing.
    """
    provider = os.getenv("EMAIL_PROVIDER", "postmark").lower()
    if provider == "postmark":
        api_key = os.getenv("POSTMARK_API_KEY")
        if not api_key:
            raise ValueError("POSTMARK_API_KEY environment variable is required for PostmarkProvider.")
        return PostmarkProvider(api_key)
    raise ValueError(f"Unsupported email provider: {provider}")
