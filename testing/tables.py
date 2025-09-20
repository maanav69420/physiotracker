# tables.py

TABLES = {}

TABLES['info'] = (
    "CREATE TABLE IF NOT EXISTS info ("
    "   name VARCHAR(100) NOT NULL,"
    "   email VARCHAR(100) NOT NULL"
    ")"
)

TABLES['department'] = (
    "CREATE TABLE IF NOT EXISTS department ("
    "   name VARCHAR(100) NOT NULL,"
    "   department VARCHAR(100) NOT NULL"
    ")"
)

TABLES['role'] = (
    "CREATE TABLE IF NOT EXISTS role ("
    "   name VARCHAR(100) NOT NULL,"
    "   rolw VARCHAR(100) NOT NULL"   # kept as per your original
    ")"
)

TABLES['item_details'] = (
    "CREATE TABLE IF NOT EXISTS item_details ("
    "   department VARCHAR(100) NOT NULL,"
    "   role VARCHAR(100) NOT NULL,"
    "   items VARCHAR(100) NOT NULL,"
    "   quantity INT NOT NULL"
    ")"
)
