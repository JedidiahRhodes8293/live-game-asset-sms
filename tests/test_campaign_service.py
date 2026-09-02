from datetime import datetime, timezone

import pytest

from game_campaigns.campaign_service import run_campaign
from game_campaigns.models import CampaignRequest


class RecordingSms:
    def __init__(self) -> None:
        self.sends: list[tuple[str, str, str]] = []

    async def send(self, to: str, body: str, idempotency_key: str) -> str:
        self.sends.append((to, body, idempotency_key))
        return "sms-1"

    async def status(self, message_id: str) -> str:
        assert message_id == "sms-1"
        return "queued"


@pytest.mark.asyncio
async def test_only_approved_asset_for_live_event_is_sent() -> None:
    request = CampaignRequest.model_validate(
        {
            "campaign_id": "launch-18",
            "sent_at": datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
            "events": [
                {"event_id": "live", "title": "Arena Finals", "starts_at": "2026-08-30T09:00:00Z", "ends_at": "2026-08-30T11:00:00Z"},
                {"event_id": "done", "title": "Qualifier", "starts_at": "2026-08-29T09:00:00Z", "ends_at": "2026-08-29T11:00:00Z"},
            ],
            "assets": [
                {"asset_id": "approved", "player_id": "player-7", "event_id": "live", "kind": "banner", "moderation": "approved"},
                {"asset_id": "review", "player_id": "player-8", "event_id": "live", "kind": "clip", "moderation": "queued"},
                {"asset_id": "old", "player_id": "player-9", "event_id": "done", "kind": "banner", "moderation": "approved"},
            ],
            "audience": [
                {"player_id": "player-7", "phone": "+15555550111", "asset_id": "approved"},
                {"player_id": "player-8", "phone": "+15555550112", "asset_id": "review"},
                {"player_id": "player-9", "phone": "+15555550113", "asset_id": "old"},
            ],
        }
    )
    sms = RecordingSms()

    result = await run_campaign(request, sms)

    assert sms.sends == [
        (
            "+15555550111",
            "Arena Finals is live now. Join player-7 in game.",
            "launch-18:player-7:approved",
        )
    ]
    assert result.messages[0].model_dump() == {
        "player_id": "player-7",
        "asset_id": "approved",
        "message_id": "sms-1",
        "status": "queued",
    }
    assert [item.reason for item in result.skipped] == ["moderation_pending", "event_not_live"]
