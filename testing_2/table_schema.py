# tables.py
TABLES = {}

TABLES['staff'] = (
    "CREATE TABLE IF NOT EXISTS staff ("
    "  staff_key INT NOT NULL AUTO_INCREMENT PRIMARY KEY,"
    "  first_name VARCHAR(50) NOT NULL,"
    "  second_name VARCHAR(50) NULL,"
    "  email VARCHAR(100) NOT NULL UNIQUE"
    ") ENGINE=InnoDB"
)

TABLES['departments'] = (
    "CREATE TABLE IF NOT EXISTS departments ("
    "  depart_key INT NOT NULL AUTO_INCREMENT PRIMARY KEY,"
    "  department VARCHAR(100) NOT NULL UNIQUE"
    ") ENGINE=InnoDB"
)

TABLES['roles'] = (
    "CREATE TABLE IF NOT EXISTS roles ("
    "  role_key INT NOT NULL AUTO_INCREMENT PRIMARY KEY,"
    "  role VARCHAR(50) NOT NULL UNIQUE"
    ") ENGINE=InnoDB"
)

TABLES['items'] = (
    "CREATE TABLE IF NOT EXISTS items ("
    "  item_key INT NOT NULL AUTO_INCREMENT PRIMARY KEY,"
    "  department INT NOT NULL,"
    "  item VARCHAR(100) NOT NULL,"
    "  default_qty INT NOT NULL,"
    "  current_qty INT NOT NULL,"
    "  FOREIGN KEY (department) REFERENCES departments(depart_key)"
    "    ON DELETE CASCADE ON UPDATE CASCADE,"
    "  UNIQUE (department, item)"
    ") ENGINE=InnoDB"
)

TABLES['staff_role_department'] = (
    "CREATE TABLE IF NOT EXISTS staff_role_department ("
    "  staff INT NOT NULL,"
    "  role INT NOT NULL,"
    "  department INT NOT NULL,"
    "  FOREIGN KEY (staff) REFERENCES staff(staff_key)"
    "    ON DELETE CASCADE ON UPDATE CASCADE,"
    "  FOREIGN KEY (role) REFERENCES roles(role_key)"
    "    ON DELETE CASCADE ON UPDATE CASCADE,"
    "  FOREIGN KEY (department) REFERENCES departments(depart_key)"
    "    ON DELETE CASCADE ON UPDATE CASCADE"
    ") ENGINE=InnoDB"
)
