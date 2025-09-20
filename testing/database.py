import mysql.connector
from tables import TABLES


# ================== DB INIT ==================
def init_db():
    """Ensure database and tables exist, return db + cursor"""
    root_db = mysql.connector.connect(
        host='localhost',
        user='root',
        passwd='root'
    )
    cursor = root_db.cursor()
    cursor.execute('SHOW DATABASES')
    dbs = [x[0] for x in cursor.fetchall()]

    if "manage_db" not in dbs:
        cursor.execute("CREATE DATABASE manage_db")
        print("Database 'manage_db' created.")

    db = mysql.connector.connect(
        host='localhost',
        user='root',
        passwd='root',
        database='manage_db'
    )
    cursor = db.cursor()

    cursor.execute("SHOW TABLES")
    existing_tables = [x[0] for x in cursor.fetchall()]

    for table_name, ddl in TABLES.items():
        if table_name not in existing_tables:
            print(f"Creating table `{table_name}`...")
            cursor.execute(ddl)
        else:
            print(f"Table `{table_name}` already exists.")

    return db, cursor


# ================== VALIDATION ==================
def validate_admin(cursor, email):
    query = """
        SELECT r.rolw FROM info i
        JOIN role r ON i.name = r.name
        WHERE i.email = %s
    """
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    return result and result[0].lower() == "admin"


def validate_staff(cursor, email):
    query = """
        SELECT r.rolw FROM info i
        JOIN role r ON i.name = r.name
        WHERE i.email = %s
    """
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    return result and result[0].lower() == "staff"


# ================== ADMIN OPS ==================
def add_record(db, cursor, table, values):
    if table == "info":
        cursor.execute("INSERT INTO info VALUES (%s, %s)", values)
    elif table == "department":
        cursor.execute("INSERT INTO department VALUES (%s, %s)", values)
    elif table == "role":
        cursor.execute("INSERT INTO role VALUES (%s, %s)", values)
    else:
        raise ValueError("Invalid table name")
    db.commit()


def update_record(db, cursor, table, name, new_value):
    if table == "info":
        cursor.execute("UPDATE info SET email=%s WHERE name=%s", (new_value, name))
    elif table == "department":
        cursor.execute("UPDATE department SET department=%s WHERE name=%s", (new_value, name))
    elif table == "role":
        cursor.execute("UPDATE role SET rolw=%s WHERE name=%s", (new_value, name))
    else:
        raise ValueError("Invalid table name")
    db.commit()


def delete_record(db, cursor, table, name):
    cursor.execute(f"DELETE FROM {table} WHERE name=%s", (name,))
    db.commit()


def display_staff(cursor):
    query = """
        SELECT i.name, i.email, d.department, r.rolw
        FROM info i
        JOIN department d ON i.name = d.name
        JOIN role r ON i.name = r.name
    """
    cursor.execute(query)
    return cursor.fetchall()


# ================== STAFF OPS ==================
def get_staff_info(cursor, email):
    query = """
        SELECT d.department, r.rolw
        FROM info i
        JOIN department d ON i.name = d.name
        JOIN role r ON i.name = r.name
        WHERE i.email = %s
    """
    cursor.execute(query, (email,))
    return cursor.fetchone()


def get_items(cursor, dept, role):
    cursor.execute("SELECT * FROM item_details WHERE department=%s AND role=%s", (dept, role))
    return cursor.fetchall()


def list_all_items(cursor):
    """Return all distinct item names from item_details table"""
    cursor.execute("SELECT DISTINCT items FROM item_details")
    return [row[0] for row in cursor.fetchall()]


def add_or_update_item(db, cursor, dept, role, item, qty):
    """Add a new item or update existing one, ensuring max quantity <= 10"""
    cursor.execute(
        "SELECT quantity FROM item_details WHERE department=%s AND role=%s AND items=%s",
        (dept, role, item)
    )
    result = cursor.fetchone()

    if result:
        current_qty = result[0]
        if current_qty + qty > 10:
            print(f"Cannot add. Max quantity is 10. Current: {current_qty}")
            return
        cursor.execute(
            "UPDATE item_details SET quantity=%s WHERE department=%s AND role=%s AND items=%s",
            (current_qty + qty, dept, role, item)
        )
        print(f"Updated {item}: now {current_qty + qty}")
    else:
        if qty > 10:
            print("Cannot add new item. Max quantity is 10.")
            return
        cursor.execute(
            "INSERT INTO item_details VALUES (%s, %s, %s, %s)",
            (dept, role, item, qty)
        )
        print(f"Added new item {item} with quantity {qty}")
    db.commit()


def delete_item(db, cursor, dept, role, item):
    cursor.execute("DELETE FROM item_details WHERE department=%s AND role=%s AND items=%s", (dept, role, item))
    db.commit()
