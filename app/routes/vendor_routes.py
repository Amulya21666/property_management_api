# app/routes/vendor_routes.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vendor, User
from app.utils import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ✅ Show all vendors (Manage Vendors Page)
@router.get("/owner/manage_vendors", response_class=HTMLResponse)
def manage_vendors(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "owner":
        return RedirectResponse(url="/dashboard", status_code=303)

    vendors = db.query(Vendor).all()
    return templates.TemplateResponse("manage_vendors.html", {"request": request, "vendors": vendors, "user": current_user})


# ✅ Add vendor (plumber, electrician, etc.)
@router.post("/owner/add_vendor")
def add_vendor(
    request: Request,
    name: str = Form(...),
    service_type: str = Form(...),  # e.g., plumber, electrician
    contact: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "owner":
        return RedirectResponse(url="/dashboard", status_code=303)

    vendor = Vendor(name=name, service_type=service_type, contact=contact)
    db.add(vendor)
    db.commit()
    return RedirectResponse(url="/owner/manage_vendors", status_code=303)


# ✅ Delete vendor
@router.post("/owner/delete_vendor/{vendor_id}")
def delete_vendor(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "owner":
        return RedirectResponse(url="/dashboard", status_code=303)

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if vendor:
        db.delete(vendor)
        db.commit()
    return RedirectResponse(url="/owner/manage_vendors", status_code=303)




@router.get("/vendor/issues")
def vendor_issues(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Get issues assigned to this vendor
    issues = db.query(Issue).filter(Issue.vendor_id == current_user.id).all()
    return templates.TemplateResponse("vendor_issues.html", {"request": request, "issues": issues})


@router.post("/vendor/submit_bill/{issue_id}")
def submit_bill(issue_id: int, bill_amount: float = Form(...), db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.vendor_id == current_user.id).first()
    if not issue:
        return RedirectResponse("/vendor/issues", status_code=302)

    issue.bill_amount = bill_amount
    issue.status = "completed"
    issue.completed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/vendor/issues", status_code=302)
