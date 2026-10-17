"""Platform connectors and factory."""

from __future__ import annotations

from agency_engine.domain.enums import PlatformName
from agency_engine.platforms.base import AdsPlatform, ResilientHttpClient
from agency_engine.platforms.fakes import FakePlatformAdapter
from agency_engine.platforms.google_ads import GoogleAdsPlatformAdapter
from agency_engine.platforms.linkedin import LinkedInPlatformAdapter
from agency_engine.platforms.meta import MetaPlatformAdapter
from agency_engine.platforms.snapchat import SnapchatPlatformAdapter
from agency_engine.platforms.tiktok import TikTokPlatformAdapter
from agency_engine.security.secret_provider import SecretProvider

__all__ = [
    "AdsPlatform",
    "FakePlatformAdapter",
    "GoogleAdsPlatformAdapter",
    "LinkedInPlatformAdapter",
    "MetaPlatformAdapter",
    "ResilientHttpClient",
    "SnapchatPlatformAdapter",
    "TikTokPlatformAdapter",
    "get_platform_adapter",
]


def get_platform_adapter(
    platform: PlatformName,
    client_slug: str,
    secret_provider: SecretProvider,
    secret_ref: str,
    use_fakes: bool = True,
) -> AdsPlatform:
    """Factory to retrieve a platform adapter (fake for testing/staging, real for production)."""
    if use_fakes:
        return FakePlatformAdapter(platform_name=platform, client_slug=client_slug)

    secret = secret_provider.get_secret(secret_ref)
    if platform == PlatformName.META:
        return MetaPlatformAdapter(access_token=secret, client_slug=client_slug)
    elif platform == PlatformName.GOOGLE_ADS:
        return GoogleAdsPlatformAdapter(
            developer_token="dev_tok",
            client_id="cid",
            client_secret="csec",
            refresh_token=secret,
            client_slug=client_slug,
        )
    elif platform == PlatformName.LINKEDIN:
        return LinkedInPlatformAdapter(access_token=secret, client_slug=client_slug)
    elif platform == PlatformName.TIKTOK:
        return TikTokPlatformAdapter(access_token=secret, client_slug=client_slug)
    elif platform == PlatformName.SNAPCHAT:
        return SnapchatPlatformAdapter(access_token=secret, client_slug=client_slug)

    raise ValueError(f"Unsupported platform: {platform}")
