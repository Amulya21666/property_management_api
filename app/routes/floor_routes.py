from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os, shutil

from app.database import get_db
from app.models import Floor, Property
from app.floorplan_extractor import extract_floorplan_details

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Directory to store uploaded floor plans
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- GET route: show Add Floor form ---
@router.get("/add_floor")
def add_floor_form(request: Request, property_id: int = None, db: Session = Depends(get_db)):
    properties = db.query(Property).all()
    return templates.TemplateResponse(
        "add_floor.html",
        {
            "request": request,
            "properties": properties,
            "selected_property_id": property_id,
            "extracted_details": None
        }
    )
@router.post("/floors/add")
async def add_floor(
    request: Request,
    property_id: int = Form(...),
    floor_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1️⃣ Create new Floor object
    new_floor = Floor(floor_number=floor_name, property_id=property_id)

    # 2️⃣ Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    new_floor.floor_plan = f"/static/uploads/{file.filename}"   # ✅ corrected
    import json

    extracted_details = extract_floorplan_details(file_path)

    # Ensure we always store a string
    if isinstance(extracted_details, dict):
        new_floor.extracted_details = json.dumps(extracted_details)
    else:
        new_floor.extracted_details = str(extracted_details)

    # 4️⃣ Save to database
    db.add(new_floor)
    db.commit()
    db.refresh(new_floor)

    # 5️⃣ Re-render the same page with extracted details
    properties = db.query(Property).all()
    return templates.TemplateResponse(
        "add_floor.html",
        {
            "request": request,
            "properties": properties,
            "selected_property_id": property_id,
            "extracted_details": extracted_details
        }
    )
