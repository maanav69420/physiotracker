# tables.py

TABLES = {}

TABLES['info'] = (
    "CREATE TABLE info ("
    "  name VARCHAR(50) NOT NULL,"
    "  email VARCHAR(100) NOT NULL PRIMARY KEY,"
    "  password VARCHAR(100) NOT NULL"
    ")"
)

TABLES['department'] = (
    "CREATE TABLE department ("
    "  email VARCHAR(100) NOT NULL,"
    "  department VARCHAR(50) NOT NULL"
    ")"
)

TABLES['role'] = (
    "CREATE TABLE role ("
    "  email VARCHAR(100) NOT NULL,"
    "  rolw VARCHAR(50) NOT NULL"
    ")"
)
