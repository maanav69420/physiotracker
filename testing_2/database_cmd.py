# database.py
import os
import json
import mysql.connector
from mysql.connector import errorcode
from tables import TABLES

# ------------------------------
# CONFIG
# ------------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "manage_my_inventory"
}

INFO_DIR = "info"
DETAILS_JSON = os.path.join(INFO_DIR, "details.json")
DEPARTMENTS_DIR = os.path.join(INFO_DIR, "departments")


# ------------------------------
# CONNECTION HELPERS
# ------------------------------
def _connect_server():
    return mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )

def ensure_database():
    conn = _connect_server()
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` DEFAULT CHARACTER SET 'utf8mb4'"
    )
    cursor.close()
    conn.close()
    return mysql.connector.connect(**DB_CONFIG)

def create_tables():
    conn = ensure_database()
    cursor = conn.cursor()
    for name, ddl in TABLES.items():
        try:
            cursor.execute(ddl)
        except mysql.connector.Error as e:
            # show error but continue
            print(f"Error creating table {name}: {e}")
    cursor.close()
    conn.close()


# ------------------------------
# JSON HELPERS
# ------------------------------
def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4)


# ------------------------------
# SYNC: JSON -> DATABASE
# ------------------------------
def sync_database_with_json(base_dir=INFO_DIR):
    """Synchronize departments, roles and items from JSON files into DB."""
    if not os.path.isdir(base_dir):
        print(f"⚠️ Info directory '{base_dir}' not found.")
        return

    details_path = os.path.join(base_dir, "details.json")
    departments_path = os.path.join(base_dir, "departments")
    if not os.path.isfile(details_path) or not os.path.isdir(departments_path):
        print("⚠️ details.json or departments folder missing under info/")
        return

    details = _load_json(details_path)
    departments_list = details.get("department", [])
    roles_list = details.get("roles", [])

    conn = ensure_database()
    cursor = conn.cursor()

    # --- Departments: add new, delete removed ---
    cursor.execute("SELECT depart_key, department FROM departments")
    existing_depts = {row[1]: row[0] for row in cursor.fetchall()}  # name -> key

    # add new departments
    for dept in departments_list:
        if dept not in existing_depts:
            cursor.execute("INSERT INTO departments (department) VALUES (%s)", (dept,))
    # refresh map
    cursor.execute("SELECT depart_key, department FROM departments")
    existing_depts = {row[1]: row[0] for row in cursor.fetchall()}

    # delete departments not in JSON (will cascade-delete items and staff-role mappings)
    to_delete = [name for name in existing_depts.keys() if name not in set(departments_list)]
    for name in to_delete:
        cursor.execute("DELETE FROM departments WHERE department=%s", (name,))

    # --- Roles: add new, delete removed ---
    cursor.execute("SELECT role_key, role FROM roles")
    existing_roles = {row[1]: row[0] for row in cursor.fetchall()}

    for role in roles_list:
        if role not in existing_roles:
            cursor.execute("INSERT INTO roles (role) VALUES (%s)", (role,))
    cursor.execute("SELECT role_key, role FROM roles")
    existing_roles = {row[1]: row[0] for row in cursor.fetchall()}

    to_delete_roles = [r for r in existing_roles.keys() if r not in set(roles_list)]
    for r in to_delete_roles:
        cursor.execute("DELETE FROM roles WHERE role=%s", (r,))

    # --- Items: sync per department ---
    # build dept map again (after potential deletions)
    cursor.execute("SELECT depart_key, department FROM departments")
    dept_map = {row[1]: row[0] for row in cursor.fetchall()}  # name -> key

    # fetch existing items map: (item, depart_key) -> item_key
    cursor.execute("SELECT item_key, item, department, default_qty, current_qty FROM items")
    db_items = {}
    for row in cursor.fetchall():
        ikey, item_name, dept_key, def_q, cur_q = row
        db_items[(item_name, dept_key)] = {
            "item_key": ikey,
            "default_qty": def_q,
            "current_qty": cur_q
        }

    json_items_seen = set()

    # iterate department json files
    for filename in os.listdir(departments_path):
        if not filename.endswith(".json"):
            continue
        file_path = os.path.join(departments_path, filename)
        try:
            data = _load_json(file_path)
        except Exception as e:
            print(f"⚠️ Failed to read '{file_path}': {e}")
            continue
        # data should be { "dept_name": { "item": {"default":n,"current":m}, ... } }
        for dept_name, items in data.items():
            dept_key = dept_map.get(dept_name)
            if dept_key is None:
                print(f"⚠️ Department '{dept_name}' in {filename} not present in DB — skipping")
                continue
            for item_name, qdata in items.items():
                default_qty = int(qdata.get("default", 0))
                current_qty = int(qdata.get("current", 0))
                json_items_seen.add((item_name, dept_key))

                if (item_name, dept_key) in db_items:
                    # update if changed
                    db_entry = db_items[(item_name, dept_key)]
                    if db_entry["default_qty"] != default_qty or db_entry["current_qty"] != current_qty:
                        cursor.execute(
                            "UPDATE items SET default_qty=%s, current_qty=%s WHERE item_key=%s",
                            (default_qty, current_qty, db_entry["item_key"])
                        )
                else:
                    # insert
                    cursor.execute(
                        "INSERT INTO items (department, item, default_qty, current_qty) VALUES (%s, %s, %s, %s)",
                        (dept_key, item_name, default_qty, current_qty)
                    )

    # delete DB items that do not appear in JSON
    for (item_name, dept_key), info in db_items.items():
        if (item_name, dept_key) not in json_items_seen:
            cursor.execute("DELETE FROM items WHERE item_key=%s", (info["item_key"],))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database synced with JSON files.")


# ------------------------------
# DB -> JSON (update item JSONs from DB)
# ------------------------------
def update_json_from_db(base_dir=INFO_DIR):
    """Write current items + quantities from DB back to info/departments/<id>.json"""
    conn = ensure_database()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT depart_key, department FROM departments")
    depts = cursor.fetchall()
    for d in depts:
        dept_key = d["depart_key"]
        dept_name = d["department"]
        cursor.execute(
            "SELECT item, default_qty, current_qty FROM items WHERE department=%s",
            (dept_key,)
        )
        rows = cursor.fetchall()
        dept_obj = {dept_name: {}}
        for r in rows:
            dept_obj[dept_name][r["item"]] = {"default": int(r["default_qty"]), "current": int(r["current_qty"])}
        os.makedirs(os.path.join(base_dir, "departments"), exist_ok=True)
        path = os.path.join(base_dir, "departments", f"{dept_key}.json")
        _write_json(path, dept_obj)

    cursor.close()
    conn.close()
    # no print here to keep caller in control


# ------------------------------
# STAFF CRUD & HELPERS
# ------------------------------
def get_departments():
    conn = ensure_database()
    cursor = conn.cursor()
    cursor.execute("SELECT depart_key, department FROM departments ORDER BY depart_key")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows  # list of (key, name)

def get_roles():
    conn = ensure_database()
    cursor = conn.cursor()
    cursor.execute("SELECT role_key, role FROM roles ORDER BY role_key")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows  # list of (key, role)

def get_all_staff():
    conn = ensure_database()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT s.staff_key, s.first_name, s.second_name, s.email, r.role, d.department "
        "FROM staff s "
        "LEFT JOIN staff_role_department srd ON s.staff_key=srd.staff "
        "LEFT JOIN roles r ON srd.role=r.role_key "
        "LEFT JOIN departments d ON srd.department=d.depart_key "
        "ORDER BY s.staff_key"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def _find_staff_by_email(email):
    conn = ensure_database()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM staff WHERE email=%s", (email,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def find_staff_by_name_email(name, email):
    names = name.split(" ", 1)
    conn = ensure_database()
    cursor = conn.cursor(dictionary=True)
    if len(names) == 2:
        cursor.execute(
            "SELECT * FROM staff WHERE first_name=%s AND second_name=%s AND email=%s",
            (names[0], names[1], email)
        )
    else:
        cursor.execute("SELECT * FROM staff WHERE first_name=%s AND email=%s", (names[0], email))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def add_staff_with_role_dept(full_name, email, role_name, department_name):
    """Add a staff and assign role & department. Enforce one 'head' overall."""
    names = full_name.split(" ", 1)
    first = names[0]
    second = names[1] if len(names) > 1 else None

    conn = ensure_database()
    cursor = conn.cursor()

    # check role exists
    cursor.execute("SELECT role_key FROM roles WHERE role=%s", (role_name,))
    role_row = cursor.fetchone()
    if not role_row:
        cursor.close()
        conn.close()
        return False, f"Role '{role_name}' not found."

    role_key = role_row[0]

    # check department exists
    cursor.execute("SELECT depart_key FROM departments WHERE department=%s", (department_name,))
    dept_row = cursor.fetchone()
    if not dept_row:
        cursor.close()
        conn.close()
        return False, f"Department '{department_name}' not found."

    dept_key = dept_row[0]

    # if role is head, ensure no other head exists
    cursor.execute("SELECT role_key FROM roles WHERE role=%s", ("head",))
    head_role = cursor.fetchone()
    if role_name.lower() == "head" and head_role:
        head_key = head_role[0]
        cursor.execute("SELECT COUNT(*) FROM staff_role_department WHERE role=%s", (head_key,))
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.close()
            conn.close()
            return False, "A head already exists. Only one head allowed."

    # insert staff
    try:
        cursor.execute(
            "INSERT INTO staff (first_name, second_name, email) VALUES (%s, %s, %s)",
            (first, second, email)
        )
        staff_key = cursor.lastrowid
        # assign role & department
        cursor.execute(
            "INSERT INTO staff_role_department (staff, role, department) VALUES (%s, %s, %s)",
            (staff_key, role_key, dept_key)
        )
        conn.commit()
    except mysql.connector.Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, f"Database error: {e}"

    cursor.close()
    conn.close()
    return True, "Staff added successfully."

def remove_staff_by_email(email):
    conn = ensure_database()
    cursor = conn.cursor()
    cursor.execute("SELECT staff_key FROM staff WHERE email=%s", (email,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return False, "Staff with that email not found."
    staff_key = row[0]
    cursor.execute("DELETE FROM staff WHERE staff_key=%s", (staff_key,))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "Staff removed."

def update_staff_name_email(email, new_full_name=None, new_email=None):
    conn = ensure_database()
    cursor = conn.cursor()
    cursor.execute("SELECT staff_key FROM staff WHERE email=%s", (email,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return False, "Staff not found."
    staff_key = row[0]
    if new_full_name:
        parts = new_full_name.split(" ", 1)
        first = parts[0]
        second = parts[1] if len(parts) > 1 else None
        cursor.execute("UPDATE staff SET first_name=%s, second_name=%s WHERE staff_key=%s", (first, second, staff_key))
    if new_email:
        cursor.execute("UPDATE staff SET email=%s WHERE staff_key=%s", (new_email, staff_key))
    conn.commit()
    cursor.close()
    conn.close()
    return True, "Staff updated."

def update_staff_role_dept(email, new_role=None, new_dept=None):
    conn = ensure_database()
    cursor = conn.cursor()

    cursor.execute("SELECT staff_key FROM staff WHERE email=%s", (email,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return False, "Staff not found."
    staff_key = row[0]

    # fetch existing mapping
    cursor.execute("SELECT role, department FROM staff_role_department WHERE staff=%s", (staff_key,))
    mapping = cursor.fetchone()
    if not mapping:
        # create mapping if not exists (shouldn't normally happen)
        mapping_role = None
        mapping_dept = None
    else:
        mapping_role, mapping_dept = mapping

    if new_role:
        cursor.execute("SELECT role_key FROM roles WHERE role=%s", (new_role,))
        r = cursor.fetchone()
        if not r:
            cursor.close()
            conn.close()
            return False, f"Role '{new_role}' not found."
        new_role_key = r[0]
        # enforce single head
        if new_role.lower() == "head":
            cursor.execute("SELECT role_key FROM roles WHERE role=%s", ("head",))
            h = cursor.fetchone()
            if h:
                head_key = h[0]
                cursor.execute("SELECT COUNT(*) FROM staff_role_department WHERE role=%s AND staff!=%s", (head_key, staff_key))
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.close()
                    conn.close()
                    return False, "Another head already exists. Cannot assign head role."
        # update or insert mapping
        cursor.execute("SELECT staff FROM staff_role_department WHERE staff=%s", (staff_key,))
        exists = cursor.fetchone()
        if exists:
            cursor.execute("UPDATE staff_role_department SET role=%s WHERE staff=%s", (new_role_key, staff_key))
        else:
            # need department key (if new_dept provided, will handle below)
            dept_for_insert = mapping_dept
            if new_dept:
                cursor.execute("SELECT depart_key FROM departments WHERE department=%s", (new_dept,))
                d = cursor.fetchone()
                if not d:
                    cursor.close()
                    conn.close()
                    return False, f"Department '{new_dept}' not found."
                dept_for_insert = d[0]
            if dept_for_insert is None:
                cursor.close()
                conn.close()
                return False, "No department available to insert staff_role_department mapping."
            cursor.execute("INSERT INTO staff_role_department (staff, role, department) VALUES (%s, %s, %s)", (staff_key, new_role_key, dept_for_insert))

    if new_dept:
        cursor.execute("SELECT depart_key FROM departments WHERE department=%s", (new_dept,))
        d = cursor.fetchone()
        if not d:
            cursor.close()
            conn.close()
            return False, f"Department '{new_dept}' not found."
        new_dept_key = d[0]
        cursor.execute("SELECT staff FROM staff_role_department WHERE staff=%s", (staff_key,))
        if cursor.fetchone():
            cursor.execute("UPDATE staff_role_department SET department=%s WHERE staff=%s", (new_dept_key, staff_key))
        else:
            # need a role_key for insert; fall back to existing mapping_role if available, else fail
            if mapping_role is None:
                cursor.close()
                conn.close()
                return False, "Role mapping missing; please set role before setting department."
            cursor.execute("INSERT INTO staff_role_department (staff, role, department) VALUES (%s, %s, %s)", (staff_key, mapping_role, new_dept_key))

    conn.commit()
    cursor.close()
    conn.close()
    return True, "Staff role/department updated."


# ------------------------------
# ITEM CRUD (helpers used by interface)
# ------------------------------
def add_item(dept_key, item_name, default_qty, current_qty):
    conn = ensure_database()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (department, item, default_qty, current_qty) VALUES (%s, %s, %s, %s)",
        (dept_key, item_name, int(default_qty), int(current_qty))
    )
    conn.commit()
    cursor.close()
    conn.close()
    update_json_from_db()

def remove_item(item_name, dept_key=None):
    conn = ensure_database()
    cursor = conn.cursor()
    if dept_key is None:
        cursor.execute("DELETE FROM items WHERE item=%s", (item_name,))
    else:
        cursor.execute("DELETE FROM items WHERE item=%s AND department=%s", (item_name, dept_key))
    conn.commit()
    cursor.close()
    conn.close()
    update_json_from_db()

def update_item_quantity(item_name, new_current_qty, dept_key=None):
    conn = ensure_database()
    cursor = conn.cursor()
    if dept_key is None:
        cursor.execute("UPDATE items SET current_qty=%s WHERE item=%s", (int(new_current_qty), item_name))
    else:
        cursor.execute("UPDATE items SET current_qty=%s WHERE item=%s AND department=%s", (int(new_current_qty), item_name, dept_key))
    conn.commit()
    cursor.close()
    conn.close()
    update_json_from_db()
