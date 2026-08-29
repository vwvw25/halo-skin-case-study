from __future__ import annotations

import pytest

from meta_reporting.config import Config, ConfigError, DeliveryChannel, SourceMode

_VARS = [
    "META_REPORTING_MODE",
    "META_SOURCE",
    "META_ACCESS_TOKEN",
    "META_AD_ACCOUNT_ID",
    "META_API_VERSION",
    "SHOPIFY_SOURCE",
    "SHOPIFY_STORE",
    "SHOPIFY_ADMIN_TOKEN",
    "DELIVER_CHANNEL",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_to_fully_mock() -> None:
    config = Config.from_env()
    assert config.default_mode is SourceMode.MOCK
    assert config.is_fully_mock
    assert config.delivery is None
    assert config.meta.api_version == "v21.0"


def test_reporting_mode_sets_default_for_each_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_REPORTING_MODE", "live")
    monkeypatch.setenv("META_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("META_AD_ACCOUNT_ID", "act_123")
    monkeypatch.setenv("SHOPIFY_STORE", "halo-skin")
    monkeypatch.setenv("SHOPIFY_ADMIN_TOKEN", "shptok")

    config = Config.from_env()

    assert config.meta.mode is SourceMode.LIVE
    assert config.shopify.mode is SourceMode.LIVE
    assert not config.is_fully_mock


def test_per_source_override_beats_global(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_REPORTING_MODE", "live")
    monkeypatch.setenv("META_SOURCE", "mock")
    monkeypatch.setenv("SHOPIFY_STORE", "halo-skin")
    monkeypatch.setenv("SHOPIFY_ADMIN_TOKEN", "shptok")

    config = Config.from_env()

    assert config.meta.mode is SourceMode.MOCK
    assert config.shopify.mode is SourceMode.LIVE


def test_live_meta_without_credentials_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_SOURCE", "live")
    with pytest.raises(ConfigError, match="META_ACCESS_TOKEN"):
        Config.from_env()


def test_invalid_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_SOURCE", "sometimes")
    with pytest.raises(ConfigError, match="not a valid mode"):
        Config.from_env()


def test_delivery_channel_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DELIVER_CHANNEL", "drive")
    assert Config.from_env().delivery is DeliveryChannel.DRIVE


def test_invalid_delivery_channel_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DELIVER_CHANNEL", "carrier-pigeon")
    with pytest.raises(ConfigError, match="DELIVER_CHANNEL"):
        Config.from_env()


def test_blank_env_var_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_API_VERSION", "   ")
    assert Config.from_env().meta.api_version == "v21.0"
