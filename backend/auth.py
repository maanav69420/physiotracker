from data_store import load_data, save_data

def register_user(user_type):
    data = load_data()
    print("="*8, f" {user_type} Registration ", "="*8)
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()

    if email in data["users"]:
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

    data["users"][email] = {
        "name": name,
        "password": password,
        "role": role,
        "department": department,
        "type": user_type.lower()
    }
    save_data(data)
    print("Registration successful!")

def login_user(user_type):
    data = load_data()
    print("="*8, f" {user_type} Login ", "="*8)
    email = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    if email in data["users"] and data["users"][email]["password"] == password and data["users"][email]["type"] == user_type.lower():
        print(f"Login successful! Welcome, {data['users'][email]['name']}.")
        return True, email
    print("Invalid email or password.")
    return False, None