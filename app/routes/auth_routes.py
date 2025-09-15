import random, os
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils import hash_password, verify_password, send_otp_email, get_current_user, send_activation_email
from app import crud
from app.models import User, Property, Appliance, PendingTenant


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --------------------------
# LOGIN / LOGOUT
# --------------------------
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password."})
    if not user.is_verified:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Account not verified. Please verify OTP."})

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


# --------------------------
# REGISTRATION + OTP
# --------------------------
@router.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_post(request: Request,
                  username: str = Form(...),
                  email: str = Form(...),
                  password: str = Form(...),
                  role: str = Form(...),
                  db: Session = Depends(get_db)):

    # For tenants: check PendingTenant table instead of full User table
    if role.lower() == "tenant":
        pending = db.query(PendingTenant).filter(
            PendingTenant.email == email,
            PendingTenant.is_activated == False
        ).first()

        if not pending:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Invalid registration or already registered."
            })

        # Create tenant user
        crud.create_user(db=db, username=username, email=email, role=role, password=password)

        # Mark tenant as activated
        pending.is_activated = True
        db.commit()

        return RedirectResponse(url="/login", status_code=302)

    # Owner/Manager → OTP flow
    else:
        if crud.get_user_by_username(db, username) or crud.get_user_by_email(db, email):
            return templates.TemplateResponse("register.html", {"request": request, "error": "Username or email already exists."})

        otp_code = str(random.randint(100000, 999999))
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)

        crud.create_user_with_otp(db=db, username=username, email=email, role=role,
                                  password=password, otp=otp_code, otp_expiry=otp_expiry, is_verified=False)

        send_otp_email(to_email=email, otp=otp_code)
        return RedirectResponse(url=f"/verify_otp?email={email}", status_code=302)



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
def invite_tenant_post(request: Request, name: str = Form(...), email: str = Form(...),
                       property_id: int = Form(...), flat_no: str = Form(None), room_no: str = Form(None),
                       db: Session = Depends(get_db), user=Depends(get_current_user)):

    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if already invited
    existing = db.query(PendingTenant).filter_by(email=email, is_activated=False).first()
    if existing:
        return {"error": "Tenant already invited."}

    pending = crud.create_pending_tenant(db, name=name, email=email,
                                         property_id=property_id, flat_no=flat_no, room_no=room_no)

    send_activation_email(email, pending.activation_token)
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

    return templates.TemplateResponse("dashboard_tenant.html", {
        "request": request,
        "user": user,
        "property": property,
        "appliances": appliances
    })

