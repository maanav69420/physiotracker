from typing import List
from fastapi import APIRouter, HTTPException
from backend.schemas import RoleIn
from backend.common import load_data, save_data

router = APIRouter(prefix="/roles", tags=["roles"])

@router.get("", response_model=List[str])
def list_roles():
    data = load_data()
    return data.get("roles", [])

@router.post("")
def add_role(r: RoleIn):
    data = load_data()
    roles = data.setdefault("roles", [])
    if r.name in roles:
        raise HTTPException(status_code=400, detail="Role exists")
    roles.append(r.name)
    save_data(data)
    return {"success": True, "role": r.name}

@router.put("/{old}")
def update_role(old: str, r: RoleIn):
    data = load_data()
    roles = data.setdefault("roles", [])
    if old not in roles:
        raise HTTPException(status_code=404, detail="Role not found")
    idx = roles.index(old)
    roles[idx] = r.name
    save_data(data)
    return {"success": True, "old": old, "new": r.name}

@router.delete("/{name}")
def del_role(name: str):
    data = load_data()
    roles = data.get("roles", [])
    if name in roles:
        roles.remove(name)
        save_data(data)
        return {"success": True, "removed": name}
    raise HTTPException(status_code=404, detail="Role not found")