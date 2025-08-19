class SmsService:
    """Provider-agnostic SMS sender interface."""

    def send(self, to: str, body: str, meta: dict | None = None) -> None:
        """Send an SMS message.
        Args:
            to: Phone number in E.164 or local format.
            body: Message body.
            meta: Optional metadata (e.g., lead_id, org_id).
        """
        raise NotImplementedError("SmsService.send() must be implemented by a provider-specific subclass.")
