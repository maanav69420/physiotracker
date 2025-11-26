from data_store import load_data, save_data

# admins and staff are separate in load_data/save_data as 'admins' and 'staff'

def register_user(user_type):
    data = load_data()
    print("="*8, f" {user_type} Registration ", "="*8)

    # require non-empty name, email and password
    while True:
        name = input("Enter your name: ").strip()
        if not name:
            print("Name cannot be empty. Please try again.")
            continue
        email = input("Enter your email: ").strip()
        if not email:
            print("Email cannot be empty. Please try again.")
            continue
        password = input("Enter your password: ").strip()
        if not password:
            print("Password cannot be empty. Please try again.")
            continue
        break

    # check in appropriate dicts
    if email in data.get("admins", {}) or email in data.get("staff", {}):
        print("Email already registered. Please try logging in.")
        return

    if user_type.lower() == "admin":
        role = "Head"
        department = "Office"
    else:
        available_roles = [r for r in data["roles"] if r != "Head"]
        available_departments = [d for d in data["departments"] if d != "Office"]
        print("Available roles:", available_roles)
        role = input("Enter your role (or press enter for default): ").strip() or "Default Role"
        if role == "Head":
            print("Role 'Head' is not allowed for staff.")
            role = "Default Role"
        print("Available departments:", available_departments)
        department = input("Enter your department (or press enter for default): ").strip() or "Default Department"
        if department == "Office":
            print("Department 'Office' is not allowed for staff.")
            department = "Default Department"

    if role not in data["roles"]:
        data["roles"].append(role)
    if department not in data["departments"]:
        data["departments"].append(department)

    if user_type.lower() == "admin":
        data.setdefault("admins", {})[email] = {
            "name": name,
            "password": password,
            "role": role,
            "department": department,
            "type": "admin"
        }
    else:
        data.setdefault("staff", {})[email] = {
            "name": name,
            "password": password,
            "role": role,
            "department": department,
            "type": "staff"
        }
    save_data(data)
    print("Registration successful!")

def login_user(user_type):
    data = load_data()
    print("="*8, f" {user_type} Login ", "="*8)
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    container = data.get("admins", {}) if user_type.lower() == "admin" else data.get("staff", {})
    if email in container and container[email]["password"] == password and container[email]["type"] == user_type.lower():
        print(f"Login successful! Welcome, {container[email]['name']}.")
        return True, email
    print("Invalid email or password.")
    return False, None