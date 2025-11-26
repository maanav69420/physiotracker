from typing import List
from fastapi import APIRouter, HTTPException
from backend.schemas import DeptIn
from backend.common import load_data, save_data

router = APIRouter(prefix="/departments", tags=["departments"])

@router.get("", response_model=List[str])
def list_depts():
    data = load_data()
    return data.get("departments", [])

@router.post("")
def add_dept(d: DeptIn):
    data = load_data()
    depts = data.setdefault("departments", [])
    if d.name in depts:
        raise HTTPException(status_code=400, detail="Department exists")
    depts.append(d.name)
    save_data(data)
    return {"success": True, "department": d.name}

@router.put("/{old}")
def update_dept(old: str, d: DeptIn):
    data = load_data()
    depts = data.setdefault("departments", [])
    if old not in depts:
        raise HTTPException(status_code=404, detail="Department not found")
    idx = depts.index(old)
    depts[idx] = d.name
    save_data(data)
    return {"success": True, "old": old, "new": d.name}

@router.delete("/{name}")
def del_dept(name: str):
    data = load_data()
    depts = data.get("departments", [])
    if name in depts:
        depts.remove(name)
        save_data(data)
        return {"success": True, "removed": name}
    raise HTTPException(status_code=404, detail="Department not found")