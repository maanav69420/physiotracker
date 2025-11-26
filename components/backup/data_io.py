import csv
import os
from datetime import datetime
from data_store import load_data, save_data

ALLOWED_KINDS = ("items", "staff", "roles", "departments")

def _next_item_id(data):
    return max([it.get("id", 0) for it in data.get("items", [])], default=0) + 1

def import_csv_file(kind: str, csv_path: str):
    """
    Import CSV into the in-app data store.
    kind: one of ALLOWED_KINDS ("items","staff","roles","departments")
    csv_path: path to CSV file
    Returns (success: bool, message: str)
    """
    kind = kind.lower()
    if kind not in ALLOWED_KINDS:
        return False, f"Unsupported kind '{kind}'. Supported: {ALLOWED_KINDS}"
    if not os.path.exists(csv_path):
        return False, f"File not found: {csv_path}"

    data = load_data()

    try:
        with open(csv_path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
    except Exception as e:
        return False, f"Failed to read CSV: {e}"

    if kind == "roles":
        added = 0
        for r in rows:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            if name not in data["roles"]:
                data["roles"].append(name)
                added += 1
        save_data(data)
        return True, f"Imported roles: added {added} new role(s)."

    if kind == "departments":
        added = 0
        for r in rows:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            if name not in data["departments"]:
                data["departments"].append(name)
                added += 1
        save_data(data)
        return True, f"Imported departments: added {added} new department(s)."

    if kind == "staff":
        # expected columns: email,name,password,role,department[,type]
        added = 0
        updated = 0
        for r in rows:
            email = (r.get("email") or "").strip()
            if not email:
                continue
            name = (r.get("name") or "").strip() or "Unknown"
            password = (r.get("password") or "").strip() or "password"
            role = (r.get("role") or "").strip() or "Default Role"
            department = (r.get("department") or "").strip() or "Default Department"
            # enforce staff-type constraints
            if role == "Head":
                role = "Default Role"
            if department == "Office":
                department = "Default Department"
            payload = {
                "name": name,
                "password": password,
                "role": role,
                "department": department,
                "type": "staff"
            }
            if email in data.get("staff", {}):
                data["staff"][email] = payload
                updated += 1
            else:
                data.setdefault("staff", {})[email] = payload
                added += 1
            if role not in data["roles"]:
                data["roles"].append(role)
            if department not in data["departments"]:
                data["departments"].append(department)
        save_data(data)
        return True, f"Imported staff: {added} added, {updated} updated."

    if kind == "items":
        # expected columns: id,department,type,name,amount_needed,current_amount
        added = 0
        updated = 0
        for r in rows:
            # parse id if provided
            try:
                iid = int(r.get("id")) if (r.get("id") or "").strip() else None
            except Exception:
                iid = None
            department = (r.get("department") or "").strip() or "Unknown"
            itype = (r.get("type") or "").strip().lower() or "consumable"
            name = (r.get("name") or "").strip() or "Unnamed"
            try:
                amount_needed = int(r.get("amount_needed")) if (r.get("amount_needed") or "").strip() else 0
            except Exception:
                amount_needed = 0
            try:
                current_amount = int(r.get("current_amount")) if (r.get("current_amount") or "").strip() else amount_needed
            except Exception:
                current_amount = amount_needed

            # find existing by id or by department+name
            found = None
            if iid is not None:
                found = next((it for it in data["items"] if it.get("id") == iid), None)
            if found is None:
                found = next((it for it in data["items"] if it.get("department") == department and it.get("name","").lower() == name.lower()), None)
            if found:
                # update found item
                found.update({
                    "department": department,
                    "type": itype,
                    "name": name,
                    "amount_needed": amount_needed,
                    "current_amount": current_amount
                })
                updated += 1
            else:
                new_id = iid if iid is not None else _next_item_id(data)
                item = {
                    "id": new_id,
                    "department": department,
                    "type": itype,
                    "name": name,
                    "amount_needed": amount_needed,
                    "current_amount": current_amount
                }
                data["items"].append(item)
                added += 1
            if department not in data["departments"]:
                data["departments"].append(department)
        save_data(data)
        return True, f"Imported items: {added} added, {updated} updated."

    return False, "Unhandled import kind."

def export_csv_file(kind: str, out_path: str = None):
    """
    Export requested data to a CSV file.
    kind: one of ALLOWED_KINDS
    out_path: optional path; if not provided a timestamped file in cwd is created.
    Returns (success: bool, message: str, filename: str|None)
    """
    kind = kind.lower()
    if kind not in ALLOWED_KINDS:
        return False, f"Unsupported kind '{kind}'. Supported: {ALLOWED_KINDS}", None

    data = load_data()
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    default_names = {
        "roles": f"roles_{ts}.csv",
        "departments": f"departments_{ts}.csv",
        "staff": f"staff_{ts}.csv",
        "items": f"items_{ts}.csv"
    }
    filename = out_path or default_names[kind]

    try:
        with open(filename, "w", newline='', encoding='utf-8') as fh:
            if kind == "roles":
                writer = csv.writer(fh)
                writer.writerow(["name"])
                for r in data.get("roles", []):
                    writer.writerow([r])
            elif kind == "departments":
                writer = csv.writer(fh)
                writer.writerow(["name"])
                for d in data.get("departments", []):
                    writer.writerow([d])
            elif kind == "staff":
                writer = csv.writer(fh)
                writer.writerow(["email", "name", "password", "role", "department", "type"])
                for email, info in data.get("staff", {}).items():
                    writer.writerow([
                        email,
                        info.get("name", ""),
                        info.get("password", ""),
                        info.get("role", ""),
                        info.get("department", ""),
                        info.get("type", "staff")
                    ])
            elif kind == "items":
                writer = csv.writer(fh)
                writer.writerow(["id", "department", "type", "name", "amount_needed", "current_amount"])
                for it in data.get("items", []):
                    writer.writerow([
                        it.get("id", ""),
                        it.get("department", ""),
                        it.get("type", ""),
                        it.get("name", ""),
                        it.get("amount_needed", ""),
                        it.get("current_amount", "")
                    ])
        return True, f"Exported {kind} to {filename}", filename
    except Exception as e:
        return False, f"Failed to write CSV: {e}", None