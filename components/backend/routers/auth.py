from fastapi import APIRouter, HTTPException
from backend.common import load_data, save_data
from backend.schemas import RegisterIn, LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def api_register(payload: RegisterIn):
    data = load_data()
    email = payload.email
    if email in data.get("admins", {}) or email in data.get("staff", {}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_type = payload.type.lower()
    if user_type == "admin":
        role = "Head"
        department = "Office"
        data.setdefault("admins", {})[email] = {
            "name": payload.name,
            "password": payload.password,
            "role": role,
            "department": department,
            "type": "admin"
        }
    else:
        role = payload.role or "Default Role"
        department = payload.department or "Default Department"
        if role == "Head":
            role = "Default Role"
        if department == "Office":
            department = "Default Department"
        data.setdefault("staff", {})[email] = {
            "name": payload.name,
            "password": payload.password,
            "role": role,
            "department": department,
            "type": "staff"
        }
    if role not in data.get("roles", []):
        data.setdefault("roles", []).append(role)
    if department not in data.get("departments", []):
        data.setdefault("departments", []).append(department)
    save_data(data)
    return {"success": True, "email": email}

@router.post("/login")
def api_login(payload: LoginIn):
    data = load_data()
    container = data.get("admins", {}) if payload.type.lower() == "admin" else data.get("staff", {})
    user = container.get(payload.email)
    if user and user.get("password") == payload.password and user.get("type") == payload.type.lower():
        return {"success": True, "email": payload.email, "name": user.get("name")}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/profile")
def get_profile(type: str, email: str):
    """
    Return basic profile for given type ('admin' or 'staff') and email.
    Example: GET /auth/profile?type=admin&email=me@example.com
    """
    data = load_data()
    t = (type or "").lower()
    if t == "admin":
        user = data.get("admins", {}).get(email)
    elif t == "staff":
        user = data.get("staff", {}).get(email)
    else:
        raise HTTPException(status_code=400, detail="type must be 'admin' or 'staff'")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "name": user.get("name"),
        "email": email,
        "role": user.get("role"),
        "department": user.get("department"),
        "type": t
    }