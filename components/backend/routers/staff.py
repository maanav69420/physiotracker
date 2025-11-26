from fastapi import APIRouter, HTTPException
from backend.schemas import RegisterIn
from backend.common import load_data, save_data

router = APIRouter(prefix="/staff", tags=["staff"])

@router.get("")
def get_staff():
    data = load_data()
    return data.get("staff", {})

@router.get("/{email}")
def get_staff_user(email: str):
    u = load_data().get("staff", {}).get(email)
    if not u:
        raise HTTPException(status_code=404, detail="Staff not found")
    return u

@router.post("")
def create_staff(payload: RegisterIn):
    if payload.type.lower() != "staff":
        raise HTTPException(status_code=400, detail="Use /auth/register for admins")
    data = load_data()
    email = payload.email
    if email in data.get("admins", {}) or email in data.get("staff", {}):
        raise HTTPException(status_code=400, detail="Email already registered")
    data.setdefault("staff", {})[email] = {
        "name": payload.name,
        "password": payload.password,
        "role": payload.role or "Default Role",
        "department": payload.department or "Default Department",
        "type": "staff"
    }
    # ensure department/role lists include values
    if data.get("roles") is None:
        data["roles"] = []
    if data.get("departments") is None:
        data["departments"] = []
    if data[email := payload.email].get("role") not in data["roles"]:
        if payload.role:
            data.setdefault("roles", []).append(payload.role)
    if payload.department and payload.department not in data["departments"]:
        data.setdefault("departments", []).append(payload.department)
    save_data(data)
    return {"success": True, "email": email}

@router.put("/{email}")
def update_staff(email: str, payload: RegisterIn):
    data = load_data()
    staff = data.get("staff", {})
    if email not in staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    # update fields; keep type 'staff'
    staff[email] = {
        "name": payload.name,
        "password": payload.password,
        "role": payload.role or staff[email].get("role", "Default Role"),
        "department": payload.department or staff[email].get("department", "Default Department"),
        "type": "staff"
    }
    # ensure department/role lists include values
    if staff[email]["role"] not in data.setdefault("roles", []):
        data["roles"].append(staff[email]["role"])
    if staff[email]["department"] not in data.setdefault("departments", []):
        data["departments"].append(staff[email]["department"])
    save_data(data)
    return {"success": True}

@router.delete("/{email}")
def delete_staff(email: str):
    data = load_data()
    if email in data.get("staff", {}):
        del data["staff"][email]
        save_data(data)
        return {"success": True}
    raise HTTPException(status_code=404, detail="Staff not found")