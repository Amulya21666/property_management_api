from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER
from app.database import get_db
from app import crud, schemas
from app.auth import get_current_user
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

# GET route: show the add property form
@router.get("/add_property")
def add_property_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("add_property.html", {"request": request, "user": user})

# POST route: create the property
@router.post("/add_property")
def add_property(
    request: Request,
    name: str = Form(...),
    address: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # 1️⃣ Create the property
    new_property = crud.create_property(
        db,
        property=schemas.PropertyCreate(name=name, address=address),
        user_id=user.id
    )

    # 2️⃣ Log the activity
    crud.log_activity(db, user.id, f"Added property: {name}")

    db.commit()

    # 3️⃣ Redirect to dashboard
    return RedirectResponse("/dashboard", status_code=HTTP_303_SEE_OTHER)
