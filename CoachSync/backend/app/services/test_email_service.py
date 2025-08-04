import os
import pytest
from app.services.email_service import EmailService
from app.services.providers.postmark_provider import PostmarkProvider

class DummyEmailService(EmailService):
    def __init__(self):
        self.sent = []
    def send(self, to_email: str, subject: str, body: str) -> None:
        self.sent.append((to_email, subject, body))


def test_email_service_not_implemented():
    service = EmailService()
    with pytest.raises(NotImplementedError):
        service.send("test@example.com", "Subject", "Body")


def test_dummy_email_service_send():
    service = DummyEmailService()
    service.send("to@x.com", "Test", "Body")
    assert service.sent == [("to@x.com", "Test", "Body")]


def test_postmark_provider_init(monkeypatch):
    # Should not raise
    monkeypatch.setenv("POSTMARK_API_KEY", "dummy-key")
    provider = PostmarkProvider("dummy-key")
    assert hasattr(provider, "client")


def test_postmark_provider_send(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.sent = []
        class emails:
            @staticmethod
            def send(**kwargs):
                FakeClient.sent.append(kwargs)
    monkeypatch.setattr("postmarker.core.PostmarkClient", lambda server_token: FakeClient())
    provider = PostmarkProvider("dummy-key")
    provider.client.emails = FakeClient.emails
    provider.send("to@x.com", "Test", "Body")
    # Check that the email was 'sent' with correct params
    assert FakeClient.sent[0]["To"] == "to@x.com"
    assert FakeClient.sent[0]["Subject"] == "Test"
    assert FakeClient.sent[0]["HtmlBody"] == "Body"


def test_get_email_service_postmark(monkeypatch):
    from app.services import get_email_service
    monkeypatch.setenv("EMAIL_PROVIDER", "postmark")
    monkeypatch.setenv("POSTMARK_API_KEY", "dummy-key")
    monkeypatch.setattr("app.services.providers.postmark_provider.PostmarkProvider", lambda key: "ok")
    assert get_email_service() == "ok"


def test_get_email_service_invalid(monkeypatch):
    from app.services import get_email_service
    monkeypatch.setenv("EMAIL_PROVIDER", "invalid")
    with pytest.raises(ValueError):
        get_email_service()
