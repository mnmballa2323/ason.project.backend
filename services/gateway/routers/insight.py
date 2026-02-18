from fastapi import APIRouter, Depends
from ..auth import require_role
from ..services.executive_dashboard import dashboard_service
from ..services.reporting_engine import reporting_service

router = APIRouter()

@router.get("/kpi", dependencies=[Depends(require_role("Shareholder"))])
async def get_strategic_kpis():
    return await dashboard_service.get_kpis()

@router.get("/reports/board_deck", dependencies=[Depends(require_role("Shareholder"))])
async def generate_board_deck():
    return await reporting_service.generate_board_deck()

@router.get("/reports/earnings", dependencies=[Depends(require_role("Shareholder"))])
async def get_earnings_script(quarter: str = "Q4-2026"):
    return await reporting_service.get_earnings_script(quarter)
