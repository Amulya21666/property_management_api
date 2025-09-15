
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session         # ← needed
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db
from app.models import User


templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/tenant/dashboard", response_class=HTMLResponse)
def tenant_dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    # Fetch current user from DB
    current_user = db.query(User).filter(User.id == user_id).first()

    return templates.TemplateResponse("tenant_dashboard.html", {
        "request": request,
        "user": current_user
    })
