from typing import Protocol

from .models import (
    CampaignMessage,
    CampaignRequest,
    CampaignResult,
    ModerationState,
    SkippedAudience,
)


class SmsGateway(Protocol):
    async def send(self, to: str, body: str, idempotency_key: str) -> str:
        raise AssertionError("Protocol method called directly")

    async def status(self, message_id: str) -> str:
        raise AssertionError("Protocol method called directly")


async def run_campaign(request: CampaignRequest, sms: SmsGateway) -> CampaignResult:
    events = {event.event_id: event for event in request.events}
    assets = {asset.asset_id: asset for asset in request.assets}
    messages: list[CampaignMessage] = []
    skipped: list[SkippedAudience] = []

    for member in request.audience:
        asset = assets.get(member.asset_id)
        event = events.get(asset.event_id) if asset else None
        reason = None
        if asset is None or asset.player_id != member.player_id or event is None:
            reason = "asset_event_mismatch"
        elif asset.moderation != ModerationState.APPROVED:
            reason = "moderation_pending"
        elif not (event.starts_at <= request.sent_at < event.ends_at):
            reason = "event_not_live"

        if reason:
            skipped.append(
                SkippedAudience(
                    player_id=member.player_id,
                    asset_id=member.asset_id,
                    reason=reason,
                )
            )
            continue

        body = f"{event.title} is live now. Join {member.player_id} in game."
        message_id = await sms.send(
            member.phone,
            body,
            f"{request.campaign_id}:{member.player_id}:{member.asset_id}",
        )
        messages.append(
            CampaignMessage(
                player_id=member.player_id,
                asset_id=member.asset_id,
                message_id=message_id,
                status=await sms.status(message_id),
            )
        )

    return CampaignResult(
        campaign_id=request.campaign_id,
        messages=messages,
        skipped=skipped,
    )
