# database.py
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
            cursor.execute(ddl)

    return db, cursor


# ================== REGISTER ==================
def register_admin(db, cursor):
    """Register new Admin"""
    print("\n=== Register as Admin ===")
    name = input("Enter your name: ")
    email = input("Enter your email: ")
    pswd = input("Enter your password: ")

    cursor.execute("INSERT INTO info VALUES (%s, %s, %s)", (name, email, pswd))
    cursor.execute("INSERT INTO department VALUES (%s, %s)", (email, "admin"))
    cursor.execute("INSERT INTO role VALUES (%s, %s)", (email, "admin"))

    db.commit()
    print(f"✅ Admin {name} registered successfully with email {email}.")


def register_staff(db, cursor):
    """Register new Staff"""
    print("\n=== Register as Staff ===")
    name = input("Enter staff name: ")
    email = input("Enter staff email: ")
    pswd = input("Enter staff password: ")
    dept = input("Enter staff department: ")
    rolw = input("Enter staff role: ")

    cursor.execute("INSERT INTO info VALUES (%s, %s, %s)", (name, email, pswd))
    cursor.execute("INSERT INTO department VALUES (%s, %s)", (email, dept))
    cursor.execute("INSERT INTO role VALUES (%s, %s)", (email, rolw))

    db.commit()
    print(f"✅ Staff {name} registered successfully with email {email}.")


# ================== LOGIN ==================
def login_admin(cursor, email, password):
    query = """
        SELECT r.rolw FROM info i
        JOIN role r ON i.email = r.email
        WHERE i.email = %s AND i.password = %s
    """
    cursor.execute(query, (email, password))
    result = cursor.fetchone()
    return result and result[0].lower() == "admin"


def login_staff(cursor, email, password):
    query = """
        SELECT r.rolw FROM info i
        JOIN role r ON i.email = r.email
        WHERE i.email = %s AND i.password = %s
    """
    cursor.execute(query, (email, password))
    result = cursor.fetchone()
    return result and result[0].lower() == "staff"


# ================== ADMIN OPS ==================
def update_staff_department(db, cursor, email, new_dept):
    cursor.execute("UPDATE department SET department=%s WHERE email=%s", (new_dept, email))
    db.commit()
    print(f"✅ Updated department for {email} to {new_dept}")


def update_staff_role(db, cursor, email, new_role):
    cursor.execute("UPDATE role SET rolw=%s WHERE email=%s", (new_role, email))
    db.commit()
    print(f"✅ Updated role for {email} to {new_role}")


def delete_staff(db, cursor, email):
    cursor.execute("DELETE FROM info WHERE email=%s", (email,))
    cursor.execute("DELETE FROM department WHERE email=%s", (email,))
    cursor.execute("DELETE FROM role WHERE email=%s", (email,))
    db.commit()
    print(f"❌ Deleted staff with email {email}")


def display_staff(cursor):
    query = """
        SELECT i.name, i.email, d.department, r.rolw
        FROM info i
        JOIN department d ON i.email = d.email
        JOIN role r ON i.email = r.email
    """
    cursor.execute(query)
    return cursor.fetchall()
