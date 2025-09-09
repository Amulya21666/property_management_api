from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/tenant/dashboard", response_class=HTMLResponse)
def tenant_dashboard(request: Request):
    return templates.TemplateResponse("dashboard_tenant.html", {"request": request})
