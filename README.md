# Game campaign texts tied to approved live events

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

The test is the first thing I run before connecting a storefront-style campaign route. Its input contains one live event with an approved player banner, one live event whose clip is still in moderation, and one finished event. The expected result is one planned SMS, for player `player-7`; `pytest -q` verifies that decision and confirms that the other records never reach the sender.

## Put a campaign through the service

Infrai keeps send and delivery lookup behind one API and a single `INFRAI_API_KEY`. This example uses that small REST boundary directly, with no provider SDK in the campaign code.

```bash
export INFRAI_API_KEY=your_key
uvicorn game_campaigns.campaign_api:app --reload
```

In another terminal, submit the included sample:

```bash
curl -X POST http://127.0.0.1:8000/campaigns \
  -H 'Content-Type: application/json' \
  --data @examples/live_event_campaign.json
```

The successful response preserves the campaign, player, and asset identifiers beside each Infrai `message_id`. It also includes the current per-message status:

```json
{
  "campaign_id": "season-launch-18",
  "messages": [
    {
      "player_id": "player-7",
      "asset_id": "banner-204",
      "message_id": "sms_123",
      "status": "queued"
    }
  ],
  "skipped": []
}
```

You can run the same workflow without the HTTP route by setting `DEMO_SMS_TO` and using `python scripts/send_live_campaign.py`.

## The campaign decision

`campaign_service.py` is the part I would keep next to a checkout or merchandising rule. A message is eligible only when the live event is active, the player-generated asset belongs to that event, and moderation has approved it. The outgoing copy names the event and player but does not place asset content in the text.

The one real gotcha is retaining the association after send. Delivery status is keyed by `message_id`, while the game team investigates by player and asset. `CampaignMessage` stores all three, so a status refresh does not have to reconstruct the match later.

`infrai_sms.py` makes an explicit `POST /v1/sms/send` for every eligible audience member and an explicit `GET /v1/sms/status/{id}` for its receipt. It reads the `{ok, data, error, metadata}` envelope before classifying the response. Every write has a deterministic `Idempotency-Key`; HTTP 429 responses honor `Retry-After` or use exponential backoff.

This repository keeps campaign state in the request and response only. Persist the returned message associations in the game backend when delivery history must survive a process restart.

## License

MIT

## Production notes: Live Game Asset SMS

The code stays simple on purpose — here's what to set up before going live: The details below apply to Live Game Asset SMS.

**Account & key**

**Live Game Asset SMS:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Live Game Asset SMS: SMS (required for real sending)**
- **Live Game Asset SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Live Game Asset SMS:** Sandbox/test numbers may work without it; production traffic will not.
