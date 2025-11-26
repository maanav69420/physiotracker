from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from backend.schemas import ItemIn, ItemUpdate
from backend.common import load_data, save_data, send_depletion_email, import_csv_file, export_csv_file
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/items", tags=["items"])

@router.get("")
def list_items(admin: Optional[bool] = False, department: Optional[str] = None):
    data = load_data()
    items = data.get("items", [])
    if admin:
        return items
    if department:
        return [it for it in items if it.get("department") == department]
    return items

@router.get("/depleted")
def depleted_items():
    data = load_data()
    return [it for it in data.get("items", []) if it.get("current_amount", 0) == 0]

# CSV import/export endpoints must come before the parameterized route
@router.post("/import")
async def api_import(kind: str = Form(...), file: UploadFile = File(...)):
    tmp = f"tmp_import_{kind}.csv"
    content = await file.read()
    with open(tmp, "wb") as fh:
        fh.write(content)
    ok, msg = import_csv_file(kind, tmp)
    try:
        os.remove(tmp)
    except Exception:
        pass
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@router.get("/export")
def api_export(kind: str):
    ok, msg, fname = export_csv_file(kind, None)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    path = os.path.abspath(fname)
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Export file not found on server")
    return FileResponse(path, media_type="text/csv", filename=os.path.basename(path))

@router.post("")
def create_item(i: ItemIn):
    data = load_data()
    next_id = max([it.get("id", 0) for it in data.get("items", [])], default=0) + 1
    item = {
        "id": next_id,
        "department": i.department,
        "type": i.type,
        "name": i.name,
        "amount_needed": i.amount_needed,
        "current_amount": i.amount_needed
    }
    data.setdefault("items", []).append(item)
    if i.department not in data.get("departments", []):
        data.setdefault("departments", []).append(i.department)
    save_data(data)
    return item

@router.get("/{item_id}")
def get_item(item_id: int):
    data = load_data()
    it = next((x for x in data.get("items", []) if x.get("id") == item_id), None)
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    return it

@router.put("/{item_id}")
def update_item(item_id: int, upd: ItemUpdate):
    data = load_data()
    it = next((x for x in data.get("items", []) if x.get("id") == item_id), None)
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    if upd.department:
        it["department"] = upd.department
        if upd.department not in data.get("departments", []):
            data.setdefault("departments", []).append(upd.department)
    if upd.type:
        it["type"] = upd.type
    if upd.name:
        it["name"] = upd.name
    if upd.amount_needed is not None:
        it["amount_needed"] = upd.amount_needed
        it["current_amount"] = upd.amount_needed
    save_data(data)
    return it

@router.delete("/{item_id}")
def delete_item(item_id: int):
    data = load_data()
    it = next((x for x in data.get("items", []) if x.get("id") == item_id), None)
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    data["items"].remove(it)
    save_data(data)
    return {"success": True}

@router.post("/{item_id}/use")
def use_item(item_id: int, user_email: str = Form(...), amount: int = Form(...)):
    data = load_data()
    staff = data.get("staff", {})
    if user_email not in staff:
        raise HTTPException(status_code=403, detail="Unknown staff user")
    dept = staff[user_email].get("department")
    it = next((x for x in data.get("items", []) if x.get("id") == item_id and x.get("department") == dept), None)
    if not it:
        raise HTTPException(status_code=404, detail="Item not found in user's department")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if amount >= it.get("current_amount", 0):
        it["current_amount"] = 0
        save_data(data)
        try:
            send_depletion_email(it, data=data)
        except Exception:
            pass
        return {"used": amount, "current_amount": 0, "depleted": True}
    it["current_amount"] = it.get("current_amount", 0) - amount
    save_data(data)
    return {"used": amount, "current_amount": it["current_amount"], "depleted": False}

@router.post("/{item_id}/refill")
def refill_item(item_id: int, user_email: str = Form(...)):
    data = load_data()
    staff = data.get("staff", {})
    if user_email not in staff:
        raise HTTPException(status_code=403, detail="Unknown staff user")
    dept = staff[user_email].get("department")
    it = next((x for x in data.get("items", []) if x.get("id") == item_id), None)
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    if it.get("department") != dept:
        raise HTTPException(status_code=403, detail="Cannot refill item outside your department")
    it["current_amount"] = it.get("amount_needed", it.get("current_amount", 0))
    save_data(data)
    return {"refilled_to": it["current_amount"]}