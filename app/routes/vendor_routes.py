import os
from datetime import datetime
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Issue, IssueStatus
from app.utils import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/vendor/dashboard", response_class=HTMLResponse)
def vendor_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    assigned_issues = (
        db.query(Issue)
        .options(
            joinedload(Issue.property),
            joinedload(Issue.appliance),
            joinedload(Issue.tenant)
        )
        .filter(Issue.vendor_id == user.id, Issue.status == IssueStatus.assigned)
        .all()
    )

    return templates.TemplateResponse(
        "vendor_dashboard.html",
        {"request": request, "user": user, "assigned_issues": assigned_issues}
    )

# -------------------------------
# Vendor marks issue as repaired
# -------------------------------
@router.post("/vendor/mark_repaired/{issue_id}")
def mark_issue_repaired(
    issue_id: int,
    bill_amount: float = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    issue = db.query(Issue).filter(
        Issue.id == issue_id, Issue.vendor_id == current_user.id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found or not assigned to you")

    issue.status = IssueStatus.repaired
    issue.bill_amount = bill_amount
    issue.completed_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/vendor/issues", status_code=303)


# -------------------------------
# Vendor accepts issue
# -------------------------------
@router.post("/vendor/accept_issue/{issue_id}")
def accept_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    issue = db.query(Issue).filter(
        Issue.id == issue_id, Issue.vendor_id == user.id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Better: move to "in_progress" instead of re-setting to "assigned"
    issue.status = IssueStatus.in_progress
    db.commit()

    return RedirectResponse("/vendor/dashboard", status_code=303)


# -------------------------------
# Vendor rejects issue
# -------------------------------
@router.post("/vendor/reject_issue/{issue_id}")
def reject_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Not authorized")

    issue = db.query(Issue).filter(
        Issue.id == issue_id, Issue.vendor_id == user.id
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue.status = IssueStatus.pending   # back to pending
    issue.vendor_id = None               # unassign vendor
    db.commit()

    return RedirectResponse("/vendor/dashboard", status_code=303)
