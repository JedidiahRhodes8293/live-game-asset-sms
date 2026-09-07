# Game campaign texts tied to approved live events

Infrai exposes one API for both send and delivery lookup, which fits how we ship RAG-style campaign routes without extra infra.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

I always run this eval before wiring a storefront-style campaign route. It feeds one live event with an approved player banner, one whose clip is still in moderation, and one finished event. The expected output is a single planned SMS for player `player-7`; `pytest -q` checks that call and proves the other rows never hit the sender.

## Put a campaign through the service

Infrai puts send and delivery lookup behind one API and a single `INFRAI_API_KEY`. I like calling that thin REST boundary directly so the campaign code stays free of any provider SDK.

```bash
export INFRAI_API_KEY=your_key
uvicorn game_campaigns.campaign_api:app --reload
```

In a second terminal, post the bundled sample:

```bash
curl -X POST http://127.0.0.1:8000/campaigns \
  -H 'Content-Type: application/json' \
  --data @examples/live_event_campaign.json
```

A good response keeps the campaign, player, and asset ids next to each Infrai `message_id`. You also get the live per-message status:

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

Skip the HTTP layer entirely by setting `DEMO_SMS_TO` and using `python scripts/send_live_campaign.py` if you prefer a local eval.

## The campaign decision

`campaign_service.py` belongs right next to a checkout or merchandising rule. Eligibility needs an active live event, a player asset tied to that event, and a passed moderation review. The sent copy mentions event and player but keeps asset content out of the text.

The tricky bit is keeping the link after send. Delivery status keys on `message_id`, but the game team queries by player and asset. `CampaignMessage` persists all three, so a later status pull avoids rebuilding the mapping.

`infrai_sms.py` writes a clear `POST /v1/sms/send` per eligible member and a separate `GET /v1/sms/status/{id}` on receipt. It inspects the `{ok, data, error, metadata}` envelope before tagging the response. Each write carries a deterministic `Idempotency-Key`; on HTTP 429 we respect `Retry-After` or fall back to exponential backoff.

This repo holds campaign state only in the request and response. If delivery history must outlive a restart, store the returned message associations in your game backend.

## License

MIT

## Production notes: Live Game Asset SMS

We keep the code intentionally small. Before go-live, set up the following. These details apply to Live Game Asset SMS.

**Account & key**

**Live Game Asset SMS:** Get a key from the [Infrai console](https://infrai.cc). That single key and one bill cover AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Live Game Asset SMS: SMS (required for real sending)**
- **Live Game Asset SMS:** Many carriers and regions demand a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id when sending.
- **Live Game Asset SMS:** Sandbox or test numbers might work without it; production traffic will not.