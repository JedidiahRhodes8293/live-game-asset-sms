from fastapi import FastAPI, HTTPException

from .campaign_service import run_campaign
from .infrai_sms import InfraiError, InfraiSms
from .models import CampaignRequest, CampaignResult

app = FastAPI(title="Live game SMS campaigns")


@app.post("/campaigns", response_model=CampaignResult)
async def create_campaign(request: CampaignRequest) -> CampaignResult:
    try:
        async with InfraiSms() as sms:
            return await run_campaign(request, sms)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
