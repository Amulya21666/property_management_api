from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/tenant/dashboard", response_class=HTMLResponse)
def tenant_dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    # Fetch current user from DB
    current_user = db.query(User).filter(User.id == user_id).first()

    return templates.TemplateResponse("dashboard_tenant.html", {
        "request": request,
        "user": current_user
    })
