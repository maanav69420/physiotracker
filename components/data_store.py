from pathlib import Path
import os
import json
import traceback
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError, ConfigurationError
import urllib.parse

DATA_JSON = Path(__file__).parent / "data.json"
DEFAULT_DB_NAME = "physiotherapy-detail"

def _mask_uri(uri):
    try:
        if "@" in uri and "://" in uri:
            scheme, rest = uri.split("://", 1)
            creds, host = rest.split("@", 1)
            if ":" in creds:
                user, _ = creds.split(":", 1)
                return f"{scheme}://{user}:***@{host}"
        return uri
    except Exception:
        return uri

def get_mongo_client():
    uri = os.environ.get("MONGO_URI")
    if not uri:
        # no URI -> fall back to JSON but print notice
        print("data_store: MONGO_URI not set — using local data.json fallback")
        return None

    try:
        # short server selection timeout so failures are quick in CLI apps
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # ping to verify connection / credentials
        client.admin.command("ping")
        return client
    except Exception as e:
        msg = str(e)
        print("data_store: MongoDB connection failed for URI:", _mask_uri(uri))
        # frequent SRV / DNS failure hints
        if "DNS" in msg or "_mongodb._tcp" in msg or "does not exist" in msg or "Name or service not known" in msg:
            print("data_store: SRV DNS lookup failed. If you use mongodb+srv:// URIs, install dnspython:")
            print("    py -m pip install dnspython")
            print("Also verify the cluster host in Atlas -> Connect -> Driver and that your MONGO_URI was copied exactly.")
            print("To inspect SRV record (PowerShell):")
            print("    nslookup -type=SRV _mongodb._tcp.<your-cluster-host>")
            return None
        if isinstance(e, ConfigurationError):
            print("data_store: configuration error:", e)
            return None
        if isinstance(e, ServerSelectionTimeoutError):
            print("data_store: cannot reach server:", e)
            return None
        if isinstance(e, PyMongoError):
            print("data_store: pymongo error:", e)
            return None
        print("data_store: unexpected error creating MongoClient:", e)
        traceback.print_exc()
        return None

def get_db(client=None):
    client = client or get_mongo_client()
    if client is None:
        return None
    dbname = os.environ.get("MONGO_DB", DEFAULT_DB_NAME)
    return client[dbname]

def ensure_collections(db):
    if db is None:
        return
    try:
        # create useful indexes
        db.admins.create_index("_id", unique=True)
        db.staff.create_index("_id", unique=True)
        db.items.create_index("id", unique=True)
        db.roles.create_index("name", unique=True)
        db.departments.create_index("name", unique=True)
    except Exception as e:
        print("data_store: ensure_collections error:", e)

# migrate_json_to_mongo unchanged semantically but shows errors if occur
def migrate_json_to_mongo(db, json_path=DATA_JSON, overwrite=False):
    if db is None:
        print("migrate_json_to_mongo: no db provided")
        return
    if not json_path.exists():
        print("migrate_json_to_mongo: json file not found:", json_path)
        return
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("migrate_json_to_mongo: failed to read json:", e)
        return

    try:
        # users: previously a single dict; split into admins/staff on 'type'
        users = data.get("users", {})
        admins_docs = []
        staff_docs = []
        if overwrite:
            db.admins.delete_many({})
            db.staff.delete_many({})
        for email, info in users.items():
            doc = info.copy()
            doc["_id"] = email
            if doc.get("type") == "admin":
                admins_docs.append(doc)
            else:
                staff_docs.append(doc)
        if admins_docs:
            try:
                db.admins.insert_many(admins_docs, ordered=False)
            except Exception:
                pass
        if staff_docs:
            try:
                db.staff.insert_many(staff_docs, ordered=False)
            except Exception:
                pass

        # roles
        roles = [{"name": r} for r in data.get("roles", [])]
        if overwrite:
            db.roles.delete_many({})
        if roles:
            try:
                db.roles.insert_many(roles, ordered=False)
            except Exception:
                # insert_many may fail on duplicates; ignore
                pass

        # departments
        depts = [{"name": d} for d in data.get("departments", [])]
        if overwrite:
            db.departments.delete_many({})
        if depts:
            try:
                db.departments.insert_many(depts, ordered=False)
            except Exception:
                pass

        # items
        items = data.get("items", [])
        if overwrite:
            db.items.delete_many({})
        if items:
            db.items.insert_many(items, ordered=False)

        print("migrate_json_to_mongo: migration completed")
    except Exception as e:
        print("migrate_json_to_mongo: migration failed:", e)
        traceback.print_exc()

# convenience helpers
def find_admin(db, email):
    return db.admins.find_one({"_id": email}) if db is not None else None

def find_staff(db, email):
    return db.staff.find_one({"_id": email}) if db is not None else None

def upsert_admin(db, email, payload):
    if db is None:
        return
    payload_copy = payload.copy()
    payload_copy["_id"] = email
    db.admins.replace_one({"_id": email}, payload_copy, upsert=True)

def upsert_staff(db, email, payload):
    if db is None:
        return
    payload_copy = payload.copy()
    payload_copy["_id"] = email
    db.staff.replace_one({"_id": email}, payload_copy, upsert=True)

def list_depleted_items(db):
    return list(db.items.find({"current_amount": 0})) if db is not None else []

# JSON fallback load/save helpers
def _load_from_json():
    if not DATA_JSON.exists():
        # return default structure with separate admins/staff
        return {"admins": {}, "staff": {}, "roles": [], "departments": [], "items": []}
    with DATA_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)

def _save_to_json(data):
    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    with DATA_JSON.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_data():
    client = get_mongo_client()
    if client is None:
        return _load_from_json()

    try:
        db = get_db(client)
    except Exception as e:
        print("load_data: cannot get db, falling back to JSON:", e)
        return _load_from_json()

    try:
        data = {"admins": {}, "staff": {}, "roles": [], "departments": [], "items": []}

        # admins
        if "admins" in db.list_collection_names():
            for u in db.admins.find({}):
                email = u.get("_id")
                if not email:
                    continue
                u_copy = u.copy()
                u_copy.pop("_id", None)
                data["admins"][email] = u_copy

        # staff
        if "staff" in db.list_collection_names():
            for u in db.staff.find({}):
                email = u.get("_id")
                if not email:
                    continue
                u_copy = u.copy()
                u_copy.pop("_id", None)
                data["staff"][email] = u_copy

        data["roles"] = [r.get("name") for r in db.roles.find({})] if "roles" in db.list_collection_names() else []
        data["departments"] = [d.get("name") for d in db.departments.find({})] if "departments" in db.list_collection_names() else []

        if "items" in db.list_collection_names():
            items = []
            for it in db.items.find({}):
                it_copy = it.copy()
                it_copy.pop("_id", None)
                items.append(it_copy)
            data["items"] = items
        else:
            data["items"] = []

        # ensure defaults
        if "Head" not in data.get("roles", []):
            data.setdefault("roles", []).append("Head")
        if "Office" not in data.get("departments", []):
            data.setdefault("departments", []).append("Office")
        if "items" not in data:
            data["items"] = []

        return data
    except Exception as e:
        print("load_data: failed to load from MongoDB, falling back to JSON:", e)
        traceback.print_exc()
        return _load_from_json()

def save_data(data):
    client = get_mongo_client()
    if client is None:
        _save_to_json(data)
        return

    try:
        db = get_db(client)
    except Exception as e:
        print("save_data: cannot get db, saving to JSON instead:", e)
        _save_to_json(data)
        return

    try:
        # overwrite admins
        db.admins.delete_many({})
        admins_docs = []
        for email, info in data.get("admins", {}).items():
            doc = info.copy()
            doc["_id"] = email
            admins_docs.append(doc)
        if admins_docs:
            try:
                db.admins.insert_many(admins_docs, ordered=False)
            except Exception:
                pass

        # overwrite staff
        db.staff.delete_many({})
        staff_docs = []
        for email, info in data.get("staff", {}).items():
            doc = info.copy()
            doc["_id"] = email
            staff_docs.append(doc)
        if staff_docs:
            try:
                db.staff.insert_many(staff_docs, ordered=False)
            except Exception:
                pass

        # overwrite roles
        db.roles.delete_many({})
        roles_docs = [{"name": r} for r in data.get("roles", [])]
        if roles_docs:
            try:
                db.roles.insert_many(roles_docs, ordered=False)
            except Exception:
                pass

        # overwrite departments
        db.departments.delete_many({})
        dept_docs = [{"name": d} for d in data.get("departments", [])]
        if dept_docs:
            try:
                db.departments.insert_many(dept_docs, ordered=False)
            except Exception:
                pass

        # overwrite items
        db.items.delete_many({})
        items_docs = [it.copy() for it in data.get("items", [])]
        if items_docs:
            db.items.insert_many(items_docs, ordered=False)
    except Exception as e:
        print("save_data: failed to write to MongoDB, saving to JSON as fallback:", e)
        traceback.print_exc()
        _save_to_json(data)

def init_db(migrate=False, overwrite=False):
    client = get_mongo_client()
    db = get_db(client) if client is not None else None
    ensure_collections(db)
    if migrate and db is not None:
        migrate_json_to_mongo(db, json_path=DATA_JSON, overwrite=overwrite)
    return db

# Database and collection notes (streamlined setup)
# - Default database name: "physiotherapy-detail" (DEFAULT_DB_NAME)
# - Collections used:
#     - users       : user documents stored with _id = <email>
#                     fields: name, password, role, department, type
#     - roles       : documents with field "name" (string)
#     - departments : documents with field "name" (string)
#     - items       : documents representing inventory items, fields:
#                     id (int), department (string), type (consumable/non-consumable),
#                     name (string), amount_needed (int), current_amount (int)
# - Environment variables:
#     - MONGO_URI : your Atlas connection string (mongodb+srv://... or mongodb://...)
#     - MONGO_DB  : optional override for the DB name (defaults to DEFAULT_DB_NAME)
# - Notes:
#     - For mongodb+srv URIs, ensure dnspython is installed: py -m pip install dnspython
#     - Users are keyed by email in the users collection to simplify lookups and upserts.
#     - To migrate local data.json into MongoDB run: init_db(migrate=True)
#     - If SRV DNS lookups fail, use Atlas "Standard" (non-SRV) connection string or verify cluster host.