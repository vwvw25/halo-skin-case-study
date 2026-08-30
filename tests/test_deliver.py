from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest

from meta_reporting.config import Config, DeliveryChannel, SourceMode
from meta_reporting.deliver import (
    DriveDeliverer,
    EmailDeliverer,
    LocalDeliverer,
    get_deliverer,
)


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.7 fake")
    return p


def _config(channel: DeliveryChannel | None) -> Config:
    from meta_reporting.config import MetaConfig, ShopifyConfig

    return Config(
        default_mode=SourceMode.MOCK,
        meta=MetaConfig(mode=SourceMode.MOCK),
        shopify=ShopifyConfig(mode=SourceMode.MOCK),
        delivery=channel,
    )


def test_local_deliverer(pdf: Path) -> None:
    result = LocalDeliverer().deliver(pdf, subject="x")
    assert result.channel == "local"
    assert result.ok
    assert result.destination == str(pdf.resolve())


def test_get_deliverer_defaults_to_local() -> None:
    assert isinstance(get_deliverer(_config(None)), LocalDeliverer)
    assert isinstance(get_deliverer(_config(DeliveryChannel.LOCAL)), LocalDeliverer)


class _FakeSMTP:
    instances: ClassVar[list[_FakeSMTP]] = []

    def __init__(self, host: str, port: int) -> None:
        self.host, self.port = host, port
        self.tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent: list[Any] = []
        _FakeSMTP.instances.append(self)

    def __enter__(self) -> _FakeSMTP:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def starttls(self) -> None:
        self.tls = True

    def login(self, user: str, password: str) -> None:
        self.login_args = (user, password)

    def send_message(self, message: Any) -> None:
        self.sent.append(message)


def test_email_deliverer_builds_and_sends(pdf: Path) -> None:
    _FakeSMTP.instances.clear()
    deliverer = EmailDeliverer(
        host="smtp.test",
        port=587,
        username="bot@halo.test",
        password="secret",
        recipients=["client@brand.test", "lead@brand.test"],
        smtp_factory=_FakeSMTP,
    )
    result = deliverer.deliver(pdf, subject="Halo Skin weekly")
    assert result.ok and result.channel == "email"

    (smtp,) = _FakeSMTP.instances
    assert smtp.tls and smtp.login_args == ("bot@halo.test", "secret")
    message = smtp.sent[0]
    assert message["Subject"] == "Halo Skin weekly"
    assert message["To"] == "client@brand.test, lead@brand.test"
    attachments = [p for p in message.iter_attachments()]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report.pdf"


def test_email_from_env_requires_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("EMAIL_SMTP_HOST", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_TO"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="EMAIL_SMTP_HOST"):
        EmailDeliverer.from_env()


class _FakeDriveService:
    def __init__(self) -> None:
        self.created: dict[str, Any] = {}

    def files(self) -> _FakeDriveService:
        return self

    def create(self, *, body: dict[str, Any], media_body: Any, fields: str) -> _FakeDriveService:
        self.created = {"body": body, "fields": fields}
        return self

    def execute(self) -> dict[str, str]:
        return {"id": "abc123", "webViewLink": "https://drive.test/abc123"}


def test_drive_deliverer_with_injected_service(pdf: Path) -> None:
    fake = _FakeDriveService()
    result = DriveDeliverer(
        folder_id="folder-1", service=fake, media_factory=lambda path, mimetype: object()
    ).deliver(pdf, subject="x")
    assert result.ok and result.channel == "drive"
    assert result.destination == "https://drive.test/abc123"
    assert fake.created["body"]["parents"] == ["folder-1"]
