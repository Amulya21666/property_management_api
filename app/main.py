from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# --- Import all your route files ---
from app.routes import auth_routes, dashboard_routes, floor_routes, otp_routes, tenant_routes, vendor_routes
from app.database import engine, Base

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
    session_cookie="session",
    same_site="lax",
    https_only=False  # True only in production with HTTPS
)

# ✅ Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ✅ Auto-create tables
Base.metadata.create_all(bind=engine)

# ✅ Register routers
# Since owner routes are inside auth_routes.py, no separate owner_routes import is needed
app.include_router(auth_routes.router)         # includes /owner/invite_tenant_page
app.include_router(dashboard_routes.router)
app.include_router(floor_routes.router)
app.include_router(otp_routes.router)
app.include_router(tenant_routes.router)
app.include_router(vendor_routes.router)

# ✅ Redirect root to /login
@app.get("/")
def root():
    return RedirectResponse(url="/login")
