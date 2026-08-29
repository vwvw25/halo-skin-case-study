"""Runtime configuration, driven entirely by environment variables.

Each data source is independently ``mock`` or ``live`` so the pipeline can run fully offline
(the default) or against real Meta / Shopify credentials. ``META_REPORTING_MODE`` sets the
default for every source; per-source overrides take precedence.

Delivery is off unless ``DELIVER_CHANNEL`` is set. Nothing here reads secrets from disk; the
repo ships a ``.env.example`` documenting every variable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class ConfigError(RuntimeError):
    """Raised when a ``live`` source or an enabled delivery channel is missing required vars."""


class SourceMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"


class DeliveryChannel(StrEnum):
    LOCAL = "local"
    DRIVE = "drive"
    EMAIL = "email"


def _get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _mode(name: str, default: SourceMode) -> SourceMode:
    raw = _get(name)
    if raw is None:
        return default
    try:
        return SourceMode(raw.lower())
    except ValueError:
        raise ConfigError(
            f"{name}={raw!r} is not a valid mode; expected one of {[m.value for m in SourceMode]}"
        ) from None


@dataclass(frozen=True, slots=True)
class MetaConfig:
    mode: SourceMode
    access_token: str | None = None
    ad_account_id: str | None = None
    api_version: str = "v21.0"

    @classmethod
    def from_env(cls, default_mode: SourceMode) -> MetaConfig:
        mode = _mode("META_SOURCE", default_mode)
        cfg = cls(
            mode=mode,
            access_token=_get("META_ACCESS_TOKEN"),
            ad_account_id=_get("META_AD_ACCOUNT_ID"),
            api_version=_get("META_API_VERSION", "v21.0") or "v21.0",
        )
        if mode is SourceMode.LIVE:
            _require(cfg.access_token, "META_ACCESS_TOKEN", mode)
            _require(cfg.ad_account_id, "META_AD_ACCOUNT_ID", mode)
        return cfg


@dataclass(frozen=True, slots=True)
class ShopifyConfig:
    mode: SourceMode
    store: str | None = None
    admin_token: str | None = None

    @classmethod
    def from_env(cls, default_mode: SourceMode) -> ShopifyConfig:
        mode = _mode("SHOPIFY_SOURCE", default_mode)
        cfg = cls(
            mode=mode,
            store=_get("SHOPIFY_STORE"),
            admin_token=_get("SHOPIFY_ADMIN_TOKEN"),
        )
        if mode is SourceMode.LIVE:
            _require(cfg.store, "SHOPIFY_STORE", mode)
            _require(cfg.admin_token, "SHOPIFY_ADMIN_TOKEN", mode)
        return cfg


@dataclass(frozen=True, slots=True)
class Config:
    default_mode: SourceMode
    meta: MetaConfig
    shopify: ShopifyConfig
    delivery: DeliveryChannel | None

    @classmethod
    def from_env(cls) -> Config:
        default_mode = _mode("META_REPORTING_MODE", SourceMode.MOCK)
        return cls(
            default_mode=default_mode,
            meta=MetaConfig.from_env(default_mode),
            shopify=ShopifyConfig.from_env(default_mode),
            delivery=_delivery_from_env(),
        )

    @property
    def is_fully_mock(self) -> bool:
        return self.meta.mode is SourceMode.MOCK and self.shopify.mode is SourceMode.MOCK


def _delivery_from_env() -> DeliveryChannel | None:
    raw = _get("DELIVER_CHANNEL")
    if raw is None:
        return None
    try:
        return DeliveryChannel(raw.lower())
    except ValueError:
        raise ConfigError(
            f"DELIVER_CHANNEL={raw!r} is not valid; expected one of "
            f"{[c.value for c in DeliveryChannel]}"
        ) from None


def _require(value: str | None, name: str, mode: SourceMode) -> None:
    if value is None:
        raise ConfigError(f"{name} is required when the source mode is {mode.value!r}")
