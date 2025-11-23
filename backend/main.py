from typing import Optional
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, EmailStr
from data_store import load_data, save_data
from items import send_depletion_email

app = FastAPI(title="PhysioTracker API (dev)")

# --- Pydantic models ---
class RegisterModel(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = None
    department: Optional[str] = None
    type: Optional[str] = "staff"  # "admin" or "staff"

class LoginModel(BaseModel):
    email: EmailStr
    password: str
    type: Optional[str] = "staff"

class DepartmentModel(BaseModel):
    name: str

class RoleModel(BaseModel):
    name: str

class ItemModel(BaseModel):
    department: str
    type: str  # consumable / non-consumable
    name: str
    amount_needed: int

class ItemUpdateModel(BaseModel):
    department: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    amount_needed: Optional[int] = None

class UseItemModel(BaseModel):
    user_email: EmailStr
    amount: int

# --- Auth endpoints ---
@app.post("/auth/register")
def api_register(payload: RegisterModel):
    data = load_data()
    if payload.email in data["users"]:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_type = payload.type.lower()
    if user_type == "admin":
        role = "Head"
        department = "Office"
    else:
        role = payload.role or "Default Role"
        department = payload.department or "Default Department"

    if role not in data["roles"]:
        data["roles"].append(role)
    if department not in data["departments"]:
        data["departments"].append(department)

    data["users"][payload.email] = {
        "name": payload.name,
        "password": payload.password,
        "role": role,
        "department": department,
        "type": user_type
    }
    save_data(data)
    return {"ok": True, "email": payload.email}

@app.post("/auth/login")
def api_login(payload: LoginModel):
    data = load_data()
    u = data["users"].get(payload.email)
    if not u or u.get("password") != payload.password or u.get("type") != payload.type.lower():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"ok": True, "email": payload.email, "name": u.get("name")}

# --- Departments ---
@app.get("/departments")
def list_departments():
    data = load_data()
    return {"departments": data.get("departments", [])}

@app.post("/departments")
def add_department(d: DepartmentModel):
    data = load_data()
    if d.name in data["departments"]:
        raise HTTPException(status_code=400, detail="Department exists")
    data["departments"].append(d.name)
    save_data(data)
    return {"ok": True}

@app.put("/departments")
def update_department(old: str = Body(..., embed=True), new: str = Body(..., embed=True)):
    data = load_data()
    if old not in data["departments"]:
        raise HTTPException(status_code=404, detail="Department not found")
    idx = data["departments"].index(old)
    data["departments"][idx] = new
    # update existing items/users that referenced it (best-effort)
    for u in data["users"].values():
        if u.get("department") == old:
            u["department"] = new
    for it in data["items"]:
        if it.get("department") == old:
            it["department"] = new
    save_data(data)
    return {"ok": True}

@app.delete("/departments")
def delete_department(name: str = Body(..., embed=True)):
    data = load_data()
    if name not in data["departments"]:
        raise HTTPException(status_code=404, detail="Department not found")
    data["departments"].remove(name)
    # remove department from users/items where applicable (simple approach)
    for u in data["users"].values():
        if u.get("department") == name:
            u["department"] = "Unassigned"
    data["items"] = [it for it in data["items"] if it.get("department") != name]
    save_data(data)
    return {"ok": True}

# --- Roles ---
@app.get("/roles")
def list_roles():
    data = load_data()
    return {"roles": data.get("roles", [])}

@app.post("/roles")
def add_role(r: RoleModel):
    data = load_data()
    if r.name in data["roles"]:
        raise HTTPException(status_code=400, detail="Role exists")
    data["roles"].append(r.name)
    save_data(data)
    return {"ok": True}

@app.put("/roles")
def update_role(old: str = Body(..., embed=True), new: str = Body(..., embed=True)):
    data = load_data()
    if old not in data["roles"]:
        raise HTTPException(status_code=404, detail="Role not found")
    idx = data["roles"].index(old)
    data["roles"][idx] = new
    for u in data["users"].values():
        if u.get("role") == old:
            u["role"] = new
    save_data(data)
    return {"ok": True}

@app.delete("/roles")
def delete_role(name: str = Body(..., embed=True)):
    data = load_data()
    if name not in data["roles"]:
        raise HTTPException(status_code=404, detail="Role not found")
    data["roles"].remove(name)
    for u in data["users"].values():
        if u.get("role") == name:
            u["role"] = "Unassigned"
    save_data(data)
    return {"ok": True}

# --- Staff (users) ---
@app.get("/staff")
def list_staff():
    data = load_data()
    return {"users": data.get("users", {})}

@app.put("/staff/{email}")
def update_staff(email: str, payload: RegisterModel):
    data = load_data()
    if email not in data["users"]:
        raise HTTPException(status_code=404, detail="User not found")
    # update fields (basic)
    user = data["users"][email]
    user["name"] = payload.name or user.get("name")
    user["password"] = payload.password or user.get("password")
    user["role"] = payload.role or user.get("role")
    user["department"] = payload.department or user.get("department")
    save_data(data)
    return {"ok": True}

@app.delete("/staff/{email}")
def delete_staff(email: str):
    data = load_data()
    if email not in data["users"]:
        raise HTTPException(status_code=404, detail="User not found")
    del data["users"][email]
    save_data(data)
    return {"ok": True}

# --- Items ---
@app.get("/items")
def get_items(department: Optional[str] = None):
    data = load_data()
    items = data.get("items", [])
    if department:
        items = [it for it in items if it.get("department") == department]
    return {"items": items}

@app.post("/items")
def create_item(it: ItemModel):
    data = load_data()
    next_id = max([x.get("id", 0) for x in data["items"]], default=0) + 1
    item = {
        "id": next_id,
        "department": it.department,
        "type": it.type,
        "name": it.name,
        "amount_needed": it.amount_needed,
        "current_amount": it.amount_needed
    }
    data["items"].append(item)
    if it.department not in data["departments"]:
        data["departments"].append(it.department)
    save_data(data)
    return {"ok": True, "id": next_id}

@app.put("/items/{item_id}")
def update_item(item_id: int, payload: ItemUpdateModel):
    data = load_data()
    item = next((x for x in data["items"] if x["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.department:
        item["department"] = payload.department
        if payload.department not in data["departments"]:
            data["departments"].append(payload.department)
    if payload.type:
        item["type"] = payload.type
    if payload.name:
        item["name"] = payload.name
    if payload.amount_needed is not None:
        item["amount_needed"] = payload.amount_needed
        item["current_amount"] = payload.amount_needed
    save_data(data)
    return {"ok": True}

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    data = load_data()
    item = next((x for x in data["items"] if x["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    data["items"].remove(item)
    save_data(data)
    return {"ok": True}

@app.post("/items/{item_id}/use")
def use_item(item_id: int, payload: UseItemModel):
    data = load_data()
    item = next((x for x in data["items"] if x["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.user_email not in data["users"]:
        raise HTTPException(status_code=400, detail="User not found")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if payload.amount >= item.get("current_amount", 0):
        item["current_amount"] = 0
        save_data(data)
        # notify admins
        send_depletion_email(item, data=data)
        return {"ok": True, "status": "depleted"}
    item["current_amount"] = item.get("current_amount", 0) - payload.amount
    save_data(data)
    return {"ok": True, "current_amount": item["current_amount"]}

@app.post("/items/{item_id}/refill")
def refill_item(item_id: int):
    data = load_data()
    item = next((x for x in data["items"] if x["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item["current_amount"] = item.get("amount_needed", item.get("current_amount", 0))
    save_data(data)
    return {"ok": True, "current_amount": item["current_amount"]}