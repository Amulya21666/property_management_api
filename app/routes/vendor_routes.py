import os, secrets
from datetime import datetime
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vendor, User, Issue, IssueStatus
from app.utils import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
@router.get("/vendor/dashboard", response_class=HTMLResponse)
def vendor_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch issues assigned to this vendor
    issues = db.query(Issue).filter(Issue.vendor_id == user.id).all()

    return templates.TemplateResponse("vendor_dashboard.html", {
        "request": request,
        "user": user,
        "issues": issues
    })



# ✅ Show all vendors (Manage Vendors Page)
@router.get("/owner/manage_vendors", response_class=HTMLResponse)
def manage_vendors(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "owner":
        return RedirectResponse(url="/dashboard", status_code=303)

    vendors = db.query(Vendor).all()
    return templates.TemplateResponse("manage_vendors.html", {"request": request, "vendors": vendors, "user": current_user})


# ✅ Add vendor
@router.post("/owner/add_vendor")
def add_vendor(
    name: str = Form(...),
    service_type: str = Form(...),
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


# ✅ Vendor issues page
@router.get("/vendor/issues", response_class=HTMLResponse)
def vendor_issues(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    issues = db.query(Issue).filter(Issue.assigned_to == user.id).all()
    return templates.TemplateResponse("vendor_issues.html", {"request": request, "issues": issues, "user": user})


# ✅ Vendor marks issue as repaired (when logged in)
@router.post("/vendor/mark_repaired/{issue_id}")
def mark_issue_repaired(
    issue_id: int,
    bill_amount: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.assigned_to == current_user.id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found or not assigned to you")

    issue.status = IssueStatus.repaired
    issue.bill_amount = bill_amount
    issue.completed_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/vendor/issues", status_code=303)


# ✅ Manager assigns vendor
@router.post("/manager/assign_vendor/{issue_id}")
def assign_vendor(issue_id: int, vendor_id: int = Form(...),
                  db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    if current_user.role not in ("manager", "owner"):
        raise HTTPException(status_code=403, detail="Not authorized")

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not issue or not vendor:
        raise HTTPException(status_code=404, detail="Issue or vendor not found")

    # assign
    token = secrets.token_urlsafe(16)
    issue.assigned_to = vendor.id
    issue.vendor_token = token
    issue.assigned_at = datetime.utcnow()
    issue.status = IssueStatus.assigned
    db.commit()

    # build link and email
    link = f"{BASE_URL}/vendor/respond/{issue.id}?token={token}"
    subject = f"Repair assigned — Issue #{issue.id}"
    body = f"Hello {vendor.name},\n\nYou have been assigned Issue #{issue.id}.\nOpen this link to submit repair notes and bill (no login required):\n\n{link}\n\nThanks."
    try:
        from app.utils import send_email
        send_email(vendor.contact, subject, body)  # use vendor.email if available
    except Exception:
        print("[assign_vendor] email fallback — link:", link)

    return RedirectResponse(url="/manager/issues", status_code=303)


@router.get("/vendor/respond/{issue_id}", response_class=HTMLResponse)
def vendor_respond(request: Request, issue_id: int, token: str, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.vendor_token == token).first()
    if not issue:
        return HTMLResponse("<h3>❌ Invalid or expired link.</h3>", status_code=400)

    return templates.TemplateResponse("vendor_respond.html", {
        "request": request,
        "issue": issue,
        "token": token
    })

@router.post("/vendor/respond/{issue_id}")
def vendor_submit(issue_id: int, token: str, repair_notes: str = Form(...), bill_amount: float = Form(...),
                  db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.vendor_token == token).first()
    if not issue:
        return HTMLResponse("<h3>❌ Invalid or expired link.</h3>", status_code=400)

    issue.repair_notes = repair_notes
    issue.bill_amount = bill_amount
    issue.status = IssueStatus.repaired
    issue.completed_at = datetime.utcnow()
    issue.vendor_token = None  # 🔒 Invalidate token after use
    db.commit()

    return HTMLResponse("<h3>✅ Bill submitted successfully!</h3>")
