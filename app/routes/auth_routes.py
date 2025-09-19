import random, os
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.models import User, Property, Appliance, PendingTenant, Issue, IssueStatus
from app.crud import create_user, get_user_by_email
from app.utils import hash_password, verify_password, send_otp_email, get_current_user, send_activation_email
import os




router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --------------------------
# LOGIN / LOGOUT
# --------------------------
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username)

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."}
        )

    # Skip OTP verification for tenants and vendors
    if user.role not in ["tenant", "vendor"] and not user.is_verified:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Account not verified. Please verify OTP."}
        )

    # Set session
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role

    # Redirect based on role
    if user.role == "owner" or user.role == "manager":
        return RedirectResponse(url="/dashboard", status_code=302)
    elif user.role == "tenant":
        return RedirectResponse(url="/tenant/dashboard", status_code=302)
    elif user.role == "vendor":
        return RedirectResponse(url="/vendor/dashboard", status_code=302)

    # fallback
    return RedirectResponse(url="/login", status_code=302)

# --------------------------
# REGISTRATION + OTP
# --------------------------
@router.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    service_type: str = Form(None),  # ✅ Add this line for vendor
    db: Session = Depends(get_db)
):
    try:
        role = role.lower()

        if role == "tenant":
            # Handle tenant registration via PendingTenant
            pending = db.query(PendingTenant).filter(
                PendingTenant.email == email,
                PendingTenant.is_activated == False
            ).first()

            if not pending:
                return templates.TemplateResponse("register.html", {
                    "request": request,
                    "error": "Invalid registration or already registered."
                })

            user = create_user(
                db=db,
                username=username,
                email=email,
                password=password,
                role=role,
                property_id=pending.property_id,
                floor_id=pending.floor_id
            )

            # Mark tenant as activated
            pending.is_activated = True
            db.commit()
            return RedirectResponse(url="/login", status_code=302)

        elif role in ["owner", "manager"]:
            # Owner / Manager → OTP verification flow
            create_user(db=db, username=username, email=email, password=password, role=role)
            return RedirectResponse(url=f"/verify_otp?email={email}", status_code=302)

        elif role == "vendor":
            # ✅ Use the Form parameter directly
            create_user(
                db=db,
                username=username,
                email=email,
                password=password,
                role=role,
                service_type=service_type  # now correctly passed
            )
            return RedirectResponse(url="/login", status_code=302)

        else:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Invalid role selected."
            })

    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})

@router.get("/verify_otp", response_class=HTMLResponse)
def verify_otp_get(request: Request, email: str):
    return templates.TemplateResponse("verify_otp.html", {"request": request, "email": email})


@router.post("/verify_otp")
def verify_otp_post(request: Request, email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email)
    if not user:
        return templates.TemplateResponse("verify_otp.html", {"request": request, "error": "User not found.", "email": email})
    if user.otp != otp or user.otp_expiry < datetime.utcnow():
        return templates.TemplateResponse("verify_otp.html", {"request": request, "error": "Invalid or expired OTP.", "email": email})

    user.is_verified = True
    db.commit()
    return RedirectResponse(url="/login", status_code=302)


# --------------------------
# FORGOT / RESET PASSWORD
# --------------------------
@router.get("/forgot_password", response_class=HTMLResponse)
def forgot_password_get(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.post("/forgot_password")
def forgot_password_post(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email)
    if not user:
        return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "Email not registered."})

    otp_code = str(random.randint(100000, 999999))
    user.otp = otp_code
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
    send_otp_email(to_email=email, otp=otp_code)
    return RedirectResponse(url=f"/reset_password?email={email}", status_code=302)


@router.get("/reset_password", response_class=HTMLResponse)
def reset_password_get(request: Request, email: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "email": email})


@router.post("/reset_password")
def reset_password_post(request: Request, email: str = Form(...), otp: str = Form(...),
                        new_password: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email)
    if not user:
        return templates.TemplateResponse("reset_password.html", {"request": request, "error": "User not found.", "email": email})
    if user.otp != otp or user.otp_expiry < datetime.utcnow():
        return templates.TemplateResponse("reset_password.html", {"request": request, "error": "Invalid or expired OTP.", "email": email})

    user.password_hash = hash_password(new_password)
    user.is_verified = True
    db.commit()
    return RedirectResponse(url="/login", status_code=302)


# --------------------------
# OWNER: INVITE TENANT
# --------------------------
@router.get("/owner/invite_tenant_page", response_class=HTMLResponse)
def invite_tenant_page(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch all properties for this owner
    owner_properties = crud.get_properties_by_owner(db, user.id)
    # Fetch pending tenants
    pending_tenants = db.query(PendingTenant).filter(PendingTenant.is_activated == False).all()

    return templates.TemplateResponse("invite_tenant.html", {
        "request": request,
        "user": user,
        "properties": owner_properties,
        "pending_tenants": pending_tenants
    })

@router.post("/owner/invite_tenant")
def invite_tenant_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    property_id: int = Form(...),
    flat_no: str = Form(None),
    room_no: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if tenant already exists
    existing = db.query(User).filter_by(email=email).first()
    if existing:
        return {"error": "Tenant already exists."}

    # Create PendingTenant with activation token
    import uuid
    activation_token = str(uuid.uuid4())
    pending = PendingTenant(
        name=name,
        email=email,
        property_id=property_id,
        flat_no=flat_no,
        room_no=room_no,
        activation_token=activation_token,
        is_activated=False
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)

    # Send activation email
    send_activation_email(email, activation_token)

    return RedirectResponse("/owner/invite_tenant_page", status_code=303)




@router.get("/activate/{token}", response_class=HTMLResponse)
def activate_tenant_form(request: Request, token: str, db: Session = Depends(get_db)):
    token = token.strip()
    pending = db.query(PendingTenant).filter(
        PendingTenant.activation_token == token,
        PendingTenant.is_activated == False
    ).first()

    if not pending:
        return HTMLResponse(content="<h3>❌ Invalid or expired activation link.</h3>", status_code=400)

    # Show register form with tenant info pre-filled
    return templates.TemplateResponse("register.html", {
        "request": request,
        "email": pending.email,
        "role": "tenant",  # tenant role fixed
        "disable_role_select": True  # optional: hide role dropdown in template
    })


@router.post("/activate/{token}", response_class=HTMLResponse)
def activate_tenant_post(
    request: Request,
    token: str,
    name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    token = token.strip()
    pending = db.query(PendingTenant).filter(
        PendingTenant.activation_token == token,
        PendingTenant.is_activated == False
    ).first()

    if not pending:
        return HTMLResponse(content="<h3>❌ Invalid or expired activation link.</h3>", status_code=400)

    if password != confirm_password:
        return templates.TemplateResponse("activate_tenant.html", {
            "request": request,
            "token": token,
            "email": pending.email,
            "error": "Passwords do not match"
        })

    # Check duplicate email
    existing_user = crud.get_user_by_email(db, pending.email)
    if existing_user:
        return templates.TemplateResponse("activate_tenant.html", {
            "request": request,
            "token": token,
            "email": pending.email,
            "error": "User with this email already exists."
        })

    # ✅ Use CRUD helper to create tenant properly
    tenant_user = crud.activate_tenant(
        db=db,
        pending_tenant=pending,
        password=password,
        name=name,
        phone=phone
    )

    # ✅ Auto-login tenant
    request.session["user_id"] = tenant_user.id
    request.session["username"] = tenant_user.username
    request.session["role"] = tenant_user.role

    return RedirectResponse(url="/tenant/dashboard", status_code=303)

@router.get("/tenant/dashboard", response_class=HTMLResponse)
def tenant_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "tenant":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch the tenant's assigned property
    property = None
    appliances = []
    if user.property_id:
        property = db.query(Property).filter(Property.id == user.property_id).first()
        appliances = db.query(Appliance).filter(Appliance.property_id == user.property_id).all()

    return templates.TemplateResponse("tenant_dashboard.html", {
        "request": request,
        "user": user,
        "property": property,
        "appliances": appliances
    })

@router.post("/tenant/report_issue/{appliance_id}")
def report_issue(appliance_id: int, description: str = Form(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found")

    issue = Issue(
        description=description,
        tenant_id=user.id,          # <-- use tenant_id, not reported_by
        property_id=appliance.property_id,
        appliance_id=appliance.id,
        status=IssueStatus.pending
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    return {"message": "Issue reported successfully", "issue_id": issue.id}



from fastapi import Request
@router.get("/owner/issues", response_class=HTMLResponse)
def owner_issues(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Not authorized")

    # ✅ Fetch issues for properties owned by this owner
    issues = (
        db.query(Issue)
        .join(Property)
        .filter(Property.owner_id == user.id)
        .all()
    )
    return templates.TemplateResponse(
        "owner_issues.html",
        {"request": request, "issues": issues, "user": user}
    )



@router.get("/manager/issues", response_class=HTMLResponse)
def manager_issues(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")

    # ✅ Load property, tenant, appliance along with each issue
    issues = (
        db.query(Issue)
        .options(
            joinedload(Issue.property),
            joinedload(Issue.appliance),
            joinedload(Issue.tenant)
        )
        .all()
    )

    # Fetch all vendors
    vendors = db.query(User).filter(User.role == "vendor").all()

    return templates.TemplateResponse(
        "issues.html",
        {"request": request, "issues": issues, "vendors": vendors, "user": current_user}
    )



@router.get("/tenant/queries")
def tenant_queries_list(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from app.models import TenantQuery  # ✅ Import locally to avoid circular import
    queries = db.query(TenantQuery).filter(TenantQuery.reported_by_id == user.id).all()
    return {"queries": queries}


@router.post("/manager/assign_vendor/{issue_id}")
def assign_vendor(
    issue_id: int,
    vendor_id: int = Form(...),   # comes from "Select Vendor" dropdown
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ("manager", "owner"):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch issue
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Fetch vendor as a User with role 'vendor'
    vendor = db.query(User).filter(
        User.id == vendor_id, User.role == "vendor"
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # ✅ Assign issue to vendor (use vendor_id, not assigned_to)
    issue.vendor_id = vendor.id
    issue.assigned_at = datetime.utcnow()
    issue.status = IssueStatus.assigned

    db.commit()
    db.refresh(issue)

    return RedirectResponse(url="/manager/issues", status_code=303)



@router.post("/manager/approve_bill/{issue_id}")
def approve_bill(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ("manager", "owner"):
        raise HTTPException(status_code=403)

    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404)

    issue.status = IssueStatus.paid
    issue.paid_at = datetime.utcnow()
    db.commit()

    return RedirectResponse("/manager/issues", status_code=303)
