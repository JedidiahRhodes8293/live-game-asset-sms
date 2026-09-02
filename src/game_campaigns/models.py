from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ModerationState(StrEnum):
    QUEUED = "queued"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlayerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    moderation: ModerationState


class LiveEvent(BaseModel):
    event_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def ends_after_start(self) -> "LiveEvent":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class CampaignAudience(BaseModel):
    player_id: str = Field(min_length=1)
    phone: str = Field(pattern=r"^\+[1-9]\d{6,14}$")
    asset_id: str = Field(min_length=1)


class CampaignRequest(BaseModel):
    campaign_id: str = Field(min_length=1)
    sent_at: datetime
    events: list[LiveEvent] = Field(min_length=1)
    assets: list[PlayerAsset] = Field(min_length=1)
    audience: list[CampaignAudience] = Field(min_length=1, max_length=100)


class CampaignMessage(BaseModel):
    player_id: str
    asset_id: str
    message_id: str
    status: str


class SkippedAudience(BaseModel):
    player_id: str
    asset_id: str
    reason: str


class CampaignResult(BaseModel):
    campaign_id: str
    messages: list[CampaignMessage]
    skipped: list[SkippedAudience]
