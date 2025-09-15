from fastapi import APIRouter, Request, Form, Depends, HTTPException, UploadFile, File, Path
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER
from sqlalchemy.orm import Session
from datetime import date, datetime
import os, shutil, json, logging

from app import crud, models
from app.database import get_db
from app.auth import get_current_user
from app.models import User, Property, Floor, Appliance

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()
logger = logging.getLogger(__name__)

from datetime import date, timedelta

@router.get("/api/appliance-stats")
def get_appliance_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    appliances = (
        db.query(Appliance)
        .join(Property, Appliance.property_id == Property.id)
        .filter(Property.owner_id == user.id)
        .all()
    )

    total = len(appliances)
    working_count = sum(1 for a in appliances if str(a.status).strip().lower() == "working")
    health_percent = round((working_count / total) * 100, 2) if total > 0 else 0

    type_status = {}
    expiring_soon_count = 0
    today = date.today()
    warning_days = 90  # ⚡ Consider warranty expiring in next 90 days as "expiring soon"

    for a in appliances:
        # Extract main type by removing " Front"
        main_type = a.name.split(" Front")[0].strip()

        # Normalize status
        status_lower = str(a.status).strip().lower()
        if status_lower == "working":
            status = "Working"
        elif status_lower == "not working":
            status = "Not Working"
        elif status_lower == "warranty expired":
            status = "Warranty Expired"
        else:
            status = "Not Working"  # fallback

        if main_type not in type_status:
            type_status[main_type] = {"Working": 0, "Not Working": 0, "Warranty Expired": 0}

        type_status[main_type][status] += 1

        # ✅ Check expiring soon
        if a.warranty_expiry:
            if today <= a.warranty_expiry <= today + timedelta(days=warning_days):
                expiring_soon_count += 1

    return {
        "health_percent": health_percent,
        "type_status": type_status,
        "appliances_expiring_count": expiring_soon_count  # <-- now active
    }


# ---------------------- ADD APPLIANCE ---------------------- #
@router.post("/add_appliance")
async def add_appliance(
    request: Request,
    name: str = Form(...),
    model: str = Form(None),
    color: str = Form(None),
    status: str = Form(...),
    warranty_expiry: str = Form(None),
    location: str = Form(None),
    property_id: int = Form(...),
    floor_id: int = Form(...),
    front_image: UploadFile = File(None),
    detail_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can add appliances.")

    try:
        warranty_expiry_date = datetime.strptime(warranty_expiry, "%Y-%m-%d").date() if warranty_expiry else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    uploads_dir = "app/static/uploads"
    os.makedirs(uploads_dir, exist_ok=True)

    def save_file(upload_file: UploadFile, suffix: str):
        if upload_file and upload_file.filename:
            safe_filename = f"{name}_{suffix}_{upload_file.filename}".replace(" ", "_")
            file_path = os.path.join(uploads_dir, safe_filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)
            upload_file.file.close()
            return safe_filename
        return None

    front_filename = save_file(front_image, "front")
    detail_filename = save_file(detail_image, "detail")

    crud.create_appliance(
        db=db,
        user_id=user.id,
        name=name,
        model=model,
        color=color,
        status=status,
        warranty_expiry=warranty_expiry_date,
        property_id=property_id,
        floor_id=floor_id,
        location=location,
        front_image=front_filename,
        detail_image=detail_filename
    )

    return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)
@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    today = datetime.today().date()

    if user.role == "owner":
        # --- OWNER LOGIC ---
        properties = crud.get_properties_by_owner(db, user.id)
        total_properties_count = len(properties)

        floors_per_property = {p.id: crud.get_floors_by_property(db, p.id) for p in properties}
        total_floors_count = sum(len(floors) for floors in floors_per_property.values())

        appliances_per_property = {}
        expiry_alerts = []
        total_appliance_count = 0

        for prop in properties:
            appliances = crud.get_appliances_by_property(db, prop.id)
            appliances_per_property[prop.id] = appliances
            total_appliance_count += len(appliances)

            for appliance in appliances:
                if appliance.warranty_expiry:
                    days_remaining = (appliance.warranty_expiry - today).days
                    status = "expired" if days_remaining < 0 else (
                        "expiring_soon" if days_remaining <= 30 else None
                    )
                    if status:
                        expiry_alerts.append({
                            "property_name": prop.name,
                            "name": appliance.name,
                            "model": appliance.model,
                            "expiry": appliance.warranty_expiry,
                            "status": status
                        })

        appliances_expiring_count = len(expiry_alerts)
        logs = crud.get_recent_logs(db)

        all_appliances = [a for alist in appliances_per_property.values() for a in alist]

        return templates.TemplateResponse("dashboard_owner.html", {
            "request": request,
            "user": user,
            "properties": properties,
            "floors_per_property": floors_per_property,
            "appliances_per_property": appliances_per_property,
            "appliances": all_appliances,
            "expiry_alerts": expiry_alerts,
            "total_appliance_count": total_appliance_count,
            "total_properties_count": total_properties_count,
            "total_floors_count": total_floors_count,
            "appliances_expiring_count": appliances_expiring_count,
            "logs": logs
        })

    elif user.role == "manager":
        # --- MANAGER LOGIC ---
        assigned_properties = crud.get_properties_assigned_to_manager(db, user.id)
        appliances_per_property = {}
        expiry_alerts = []
        total_appliance_count = 0

        for prop in assigned_properties:
            appliances = crud.get_appliances_by_property(db, prop.id)
            appliances_per_property[prop.id] = appliances
            total_appliance_count += len(appliances)

            for appliance in appliances:
                if appliance.warranty_expiry:
                    days_remaining = (appliance.warranty_expiry - today).days
                    status = "expired" if days_remaining < 0 else (
                        "expiring_soon" if days_remaining <= 30 else None
                    )
                    if status:
                        expiry_alerts.append({
                            "property_name": prop.name,
                            "name": appliance.name,
                            "model": appliance.model,
                            "expiry": appliance.warranty_expiry,
                            "status": status
                        })

        return templates.TemplateResponse("dashboard_manager.html", {
            "request": request,
            "user": user,
            "properties": assigned_properties,
            "appliances_per_property": appliances_per_property,
            "total_appliance_count": total_appliance_count,
            "expiry_alerts": expiry_alerts,
            "today": today
        })

    elif user.role == "tenant":
        # --- TENANT LOGIC ---
        tenant_property = db.query(Property).filter(
            Property.id == user.property_id
        ).first() if user.property_id else None

        tenant_floor = db.query(Floor).filter(
            Floor.id == user.floor_id
        ).first() if user.floor_id else None

        appliances_per_property = {}
        expiry_alerts = []
        total_appliance_count = 0
        appliances = []

        if tenant_property:
            # Get appliances only in tenant's property (optionally filter by floor)
            query = db.query(Appliance).filter(Appliance.property_id == tenant_property.id)

            if tenant_floor:
                query = query.filter(Appliance.floor_id == tenant_floor.id)

            appliances = query.all()
            appliances_per_property[tenant_property.id] = appliances
            total_appliance_count = len(appliances)

            # Prepare expiry alerts
            for appliance in appliances:
                if appliance.warranty_expiry:
                    days_remaining = (appliance.warranty_expiry - today).days
                    if days_remaining < 0:
                        status = "expired"
                    elif days_remaining <= 30:
                        status = "expiring_soon"
                    else:
                        status = None

                    if status:
                        expiry_alerts.append({
                            "property_name": tenant_property.name,
                            "floor_name": tenant_floor.name if tenant_floor else None,
                            "name": appliance.name,
                            "model": appliance.model,
                            "expiry": appliance.warranty_expiry,
                            "status": status
                        })

        return templates.TemplateResponse(
            "tenant_dashboard.html",
            {
                "request": request,
                "user": user,

                "tenant_name": user.username,
                "property": tenant_property,
                "floor": tenant_floor,
                "appliances": appliances,
                "stats": {
                    "total_appliances": total_appliance_count,
                    "working": sum(1 for a in appliances if a.status == "working"),
                    "expiring_soon": len(
                        [a for a in appliances if a.warranty_expiry and 0 <= (a.warranty_expiry - today).days <= 30])
                },
                "expiry_alerts": expiry_alerts,
            }
        )

    else:
        raise HTTPException(status_code=403, detail="Unauthorized")


# ---------------------- OWNER PAGES ----------------------
@router.get("/add_property_page", response_class=HTMLResponse)
def add_property_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse("add_property.html", {"request": request, "user": user})

@router.get("/assign_property_page", response_class=HTMLResponse)
def assign_property_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    properties = crud.get_properties_by_owner(db, user.id)
    managers = crud.get_all_managers(db)
    return templates.TemplateResponse("assign_property.html", {
        "request": request,
        "user": user,
        "properties": properties,
        "managers": managers
    })


@router.get("/add_appliance_page", response_class=HTMLResponse)
def add_appliance_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    properties = crud.get_properties_by_owner(db, user.id)

    floors_dict = {
        p.id: [{"id": f.id, "floor_number": f.floor_number} for f in crud.get_floors_by_property(db, p.id)]
        for p in properties
    }

    return templates.TemplateResponse("add_appliance.html", {
        "request": request,
        "user": user,
        "properties": properties,
        "floors_json": json.dumps(floors_dict),  # used in JS
        "current_date": date.today()
    })

@router.get("/view_properties", response_class=HTMLResponse)
def view_properties(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Unauthorized")

    properties = crud.get_properties_by_owner(db, user.id)
    appliances_per_property = {}
    floors_per_property = {}

    for prop in properties:
        # Get all appliances for the property
        appliances = crud.get_appliances_by_property(db, prop.id)

        # Get all floors for the property
        floors = crud.get_floors_by_property(db, prop.id)

        # Manually attach appliances to their respective floor
        for floor in floors:
            floor.appliances = [appliance for appliance in appliances if appliance.floor_id == floor.id]

        # Save results
        appliances_per_property[prop.id] = appliances
        floors_per_property[prop.id] = floors

    return templates.TemplateResponse("view_properties.html", {
        "request": request,
        "user": user,
        "properties": properties,
        "appliances_per_property": appliances_per_property,
        "floors_per_property": floors_per_property
    })


# ---------------------- PROPERTY ----------------------
@router.post("/assign_property")
def assign_property(
    request: Request,
    property_id: int = Form(...),
    manager_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can assign properties.")

    crud.assign_property_to_manager(db, property_id, manager_id)
    return RedirectResponse("/dashboard", status_code=HTTP_303_SEE_OTHER)

@router.post("/update_property")
def update_property(
    request: Request,
    property_id: int = Form(...),
    name: str = Form(...),
    address: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can update properties.")

    crud.update_property(db, property_id, name, address)
    return RedirectResponse("/dashboard", status_code=HTTP_303_SEE_OTHER)

@router.get("/edit_property/{property_id}", response_class=HTMLResponse)
def edit_property_page(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can edit properties.")

    property_obj = crud.get_property_by_id(db, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found.")

    return templates.TemplateResponse("edit_property.html", {
        "request": request,
        "user": user,
        "property": property_obj
    })
# ---------------------- APPLIANCE ----------------------
@router.get("/edit_appliance/{appliance_id}", response_class=HTMLResponse)
def edit_appliance_page(
    appliance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role not in ["owner", "manager"]:   # ✅ allow both roles
        raise HTTPException(status_code=403, detail="Only owners/managers can edit appliances.")

    appliance = crud.get_appliance_by_id(db, appliance_id)
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found")

    return templates.TemplateResponse("edit_appliance.html", {
        "request": request,
        "appliance": appliance,
        "user": user
    })


@router.post("/update_appliance/{appliance_id}")
def update_appliance(
    appliance_id: int,
    name: str = Form(...),
    model: str = Form(...),
    color: str = Form(...),
    status: str = Form(...),
    warranty_expiry: str = Form(...),
    location: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role not in ["owner", "manager"]:   # ✅ allow both roles
        raise HTTPException(status_code=403, detail="Only owners/managers can update appliances.")

    appliance = crud.get_appliance_by_id(db, appliance_id)
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found")

    try:
        warranty_date = datetime.strptime(warranty_expiry, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    crud.update_appliance(
        db=db,
        appliance=appliance,
        name=name,
        model=model,
        color=color,
        status=status,
        warranty_expiry=warranty_date,
        location=location
    )

    # redirect back to manager/owner dashboard
    if user.role == "owner":
        return RedirectResponse(url="/dashboard", status_code=303)
    else:
        return RedirectResponse(url="/manager_dashboard", status_code=303)  # ✅ redirect manager correctly


# ---------------------- FLOOR ----------------------
@router.get("/add_floor", response_class=HTMLResponse)
def show_add_floor_form(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "owner":
        return RedirectResponse("/dashboard", status_code=303)

    properties = db.query(Property).filter(Property.owner_id == current_user.id).all()
    return templates.TemplateResponse("add_floor.html", {"request": request, "properties": properties})

@router.post("/add_floor")
def add_floor(
    request: Request,
    property_id: int = Form(...),
    floor_number: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"📥 Received form: property_id={property_id}, floor_number={floor_number}")
    if current_user.role != "owner":
        return RedirectResponse("/dashboard", status_code=303)

    # ❌ This is wrong: Floor has no field called floor_number
    # existing = db.query(Floor).filter_by(property_id=property_id, floor_number=floor_number).first()

    # ✅ Correct version
    existing = db.query(Floor).filter_by(property_id=property_id, floor_number=floor_number).first()
    if existing:
        return RedirectResponse(f"/add_floor?error=exists&property_id={property_id}", status_code=303)

    # ✅ Create with the correct field
    new_floor = Floor(floor_number=floor_number, property_id=property_id)
    db.add(new_floor)
    db.commit()
    crud.log_activity(db, current_user.id, f"Added floor '{floor_number}' to property ID {property_id}")
    return RedirectResponse("/add_floor", status_code=303)



@router.get("/edit_floor/{floor_id}", response_class=HTMLResponse)
def edit_floor_page(
    floor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can edit floors.")

    floor = db.query(Floor).filter(Floor.id == floor_id).first()
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found.")

    return templates.TemplateResponse("edit_floor.html", {
        "request": request,
        "floor": floor,
        "user": user
    })
@router.post("/update_floor/{floor_id}")
def update_floor(floor_id: int, floor_number: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    floor = db.query(Floor).filter(Floor.id == floor_id).first()
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")

    floor.floor_number = floor_number
    db.commit()
    return RedirectResponse(url="/view_properties", status_code=303)

@router.post("/add_property")
def add_property(
    name: str = Form(...),
    address: str = Form(...),
    property_type: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can add properties.")

    # ✅ Only include columns that exist in your Property model
    new_property = Property(
        name=name,
        address=address,
        property_type=property_type,
        owner_id=user.id
    )

    db.add(new_property)
    db.commit()
    db.refresh(new_property)
    crud.log_activity(db, user.id, f"Added property: {name}")

    return RedirectResponse(
        url=f"/add_floor?property_id={new_property.id}",
        status_code=303
    )


from fastapi import Path

@router.post("/delete_property/{property_id}")
def delete_property(
    property_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can delete properties.")

    property_obj = db.query(Property).filter_by(id=property_id, owner_id=user.id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found.")

    db.delete(property_obj)
    db.commit()
    crud.log_activity(db, user.id, f"Deleted property: {property_obj.name}")

    return RedirectResponse(url="/view_properties", status_code=303)

@router.get("/appliance_stats")
def appliance_stats(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_count = crud.get_total_appliance_count(db)
    return templates.TemplateResponse("appliance_stats.html", {
        "request": request,
        "total_appliance_count": total_count
    })
@router.get("/owner_dashboard", response_class=HTMLResponse)
async def owner_dashboard(request: Request, db: Session = Depends(get_db)):
    session_token = request.session.get("user")
    if not session_token:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.username == session_token).first()

    # ✅ Count appliances where owner_id matches current user
    total_appliance_count = (
        db.query(Appliance)
        .join(Property)
        .filter(Property.owner_id == user.id)
        .count()
    )

    return templates.TemplateResponse("owner_dashboard.html", {
        "request": request,
        "user": user,
        "total_appliance_count": total_appliance_count
    })

@router.post("/delete_appliance/{appliance_id}")
def delete_appliance(
    appliance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if appliance:
        db.delete(appliance)

        crud.log_activity(db, user.id, f"Deleted appliance: {appliance.name}")
        db.commit()
    return RedirectResponse(url="/view_properties", status_code=303)

@router.get("/appliance/{appliance_id}", response_class=HTMLResponse)
def appliance_detail(request: Request, appliance_id: int, db: Session = Depends(get_db),
                     user: models.User = Depends(get_current_user)):

    # Get appliance
    appliance = db.query(models.Appliance).filter(models.Appliance.id == appliance_id).first()
    if not appliance:
        return HTMLResponse(content="Appliance not found", status_code=404)

    # Authorization check
    if user.role == "owner":
        # Owner can only see appliances in their properties
        if appliance.property.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You are not allowed to view this appliance")
    elif user.role == "manager":
        # Manager can only see appliances in assigned properties
        assigned_properties = crud.get_properties_assigned_to_manager(db, user.id)
        if appliance.property_id not in [p.id for p in assigned_properties]:
            raise HTTPException(status_code=403, detail="You are not allowed to view this appliance")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Image handling
    front_image = appliance.front_image or "uploads/front_placeholder.jpg"
    detail_image = appliance.detail_image or "uploads/front_placeholder.jpg"

    return templates.TemplateResponse("appliance_details.html", {
        "request": request,
        "appliance": appliance,
        "front_image": front_image,
        "detail_image": detail_image,
        "user": user
    })

# dashboard_routes.py
# ---------------------- TENANT ASSIGNMENT ---------------------- #
@router.get("/assign_tenant_page", response_class=HTMLResponse)
def assign_tenant_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can assign tenants.")

    # ✅ Get all tenants (not yet assigned or all, depending on your CRUD)
    tenants = crud.get_all_tenants(db)

    # ✅ Get only this owner's properties
    properties = crud.get_properties_by_owner(db, user.id)

    # ✅ Collect floors for each property
    floors_per_property = {
        p.id: crud.get_floors_by_property(db, p.id) for p in properties
    }

    return templates.TemplateResponse("assign_tenant.html", {
        "request": request,
        "user": user,
        "tenants": tenants,
        "properties": properties,
        "floors_per_property": floors_per_property
    })


