import asyncio
import os
from datetime import datetime, timedelta, timezone

from game_campaigns.campaign_service import run_campaign
from game_campaigns.infrai_sms import InfraiSms
from game_campaigns.models import CampaignRequest


async def main() -> None:
    phone = os.environ.get("DEMO_SMS_TO")
    if not phone:
        raise RuntimeError("DEMO_SMS_TO is required")
    now = datetime.now(timezone.utc)
    request = CampaignRequest.model_validate(
        {
            "campaign_id": "season-launch-demo",
            "sent_at": now,
            "events": [
                {
                    "event_id": "arena-18",
                    "title": "Season 18 Arena",
                    "starts_at": now - timedelta(minutes=5),
                    "ends_at": now + timedelta(hours=2),
                }
            ],
            "assets": [
                {
                    "asset_id": "banner-demo",
                    "player_id": "demo-player",
                    "event_id": "arena-18",
                    "kind": "banner",
                    "moderation": "approved",
                }
            ],
            "audience": [
                {"player_id": "demo-player", "phone": phone, "asset_id": "banner-demo"}
            ],
        }
    )
    async with InfraiSms() as sms:
        result = await run_campaign(request, sms)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
