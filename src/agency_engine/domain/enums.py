"""Domain enumerations for the omnichannel agency engine."""

from enum import StrEnum


class PlatformName(StrEnum):
    META = "meta"
    GOOGLE_ADS = "google_ads"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"


class MetaPlacement(StrEnum):
    ALL = "ALL"  # Advantage+ Placements (Facebook + Instagram)
    INSTAGRAM = "INSTAGRAM"  # Instagram Only (Reels, Stories, Feed, Explore)
    FACEBOOK = "FACEBOOK"  # Facebook Only (Feed, Stories, Marketplace)


class AutonomyMode(StrEnum):
    READ_ONLY = "READ_ONLY"
    SHADOW = "SHADOW"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    LIMITED_AUTONOMY = "LIMITED_AUTONOMY"


class ActionType(StrEnum):
    NOOP = "NOOP"
    PAUSE = "PAUSE"
    ENABLE = "ENABLE"
    UPDATE_BUDGET = "UPDATE_BUDGET"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QualityStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class ActionState(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"
