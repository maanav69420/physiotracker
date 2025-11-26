from data_store import load_data, save_data

def manage_staff(admin=False):
    data = load_data()
    while True:
        print("="*8, " Manage Staff ", "="*8)
        if admin:
            print("Available roles:", data["roles"])
            print("Available departments:", data["departments"])
        else:
            available_roles = [r for r in data["roles"] if r != "Head"]
            available_departments = [d for d in data["departments"] if d != "Office"]
            print("Available roles:", available_roles)
            print("Available departments:", available_departments)
        print(
            '''1. Remove Staff
            2. Update Staff
            3. Back'''
        )
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                email = input("Enter staff email to remove: ")
                if email in data.get("staff", {}):
                    del data["staff"][email]
                    save_data(data)
                    print("Staff removed successfully.")
                else:
                    print("Staff not found.")
            elif choice == 2:
                if admin:
                    email = input("Enter staff email to update: ")
                    if email in data.get("staff", {}):
                        update_staff_admin(data, email)
                    else:
                        print("Staff not found.")
                else:
                    email = input("Enter staff email to update: ")
                    if email in data.get("staff", {}):
                        print("Current details:", data["staff"][email])
                        name = input("Enter new name (or press enter to keep): ") or data["staff"][email]["name"]
                        password = input("Enter new password (or press enter to keep): ") or data["staff"][email]["password"]
                        available_roles = [r for r in data["roles"] if r != "Head"]
                        print("Available roles:", available_roles)
                        role = input("Enter new role (or press enter to keep): ") or data["staff"][email]["role"]
                        if role == "Head":
                            print("Role 'Head' is not allowed for staff.")
                            role = data["staff"][email]["role"]
                        available_departments = [d for d in data["departments"] if d != "Office"]
                        print("Available departments:", available_departments)
                        department = input("Enter new department (or press enter to keep): ") or data["staff"][email]["department"]
                        if department == "Office":
                            print("Department 'Office' is not allowed for staff.")
                            department = data["staff"][email]["department"]
                        data["staff"][email] = {
                            "name": name,
                            "password": password,
                            "role": role,
                            "department": department,
                            "type": "staff"
                        }
                        save_data(data)
                        print("Staff updated successfully.")
                    else:
                        print("Staff not found.")
            elif choice == 3:
                break
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def update_staff_admin(data, email):
    user = data["staff"][email]
    while True:
        print("Current details:", user)
        print(
            '''What do you want to update?
            1. Name
            2. Email
            3. Password
            4. Department
            5. Role
            6. Back'''
        )
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                new_name = input("Enter new name: ")
                user["name"] = new_name
                print("Name updated.")
            elif choice == 2:
                new_email = input("Enter new email: ")
                if new_email in data.get("staff", {}) or new_email in data.get("admins", {}):
                    print("Email already exists.")
                else:
                    data["staff"][new_email] = user
                    del data["staff"][email]
                    email = new_email
                    print("Email updated.")
            elif choice == 3:
                new_password = input("Enter new password: ")
                user["password"] = new_password
                print("Password updated.")
            elif choice == 4:
                print("Available departments:", data["departments"])
                new_dept = input("Enter new department: ")
                if new_dept == "Office" and user["type"] == "staff":
                    print("Department 'Office' is not allowed for staff.")
                else:
                    user["department"] = new_dept
                    if new_dept not in data["departments"]:
                        data["departments"].append(new_dept)
                    print("Department updated.")
            elif choice == 5:
                print("Available roles:", data["roles"])
                new_role = input("Enter new role: ")
                if new_role == "Head" and user["type"] == "staff":
                    print("Role 'Head' is not allowed for staff.")
                else:
                    user["role"] = new_role
                    if new_role not in data["roles"]:
                        data["roles"].append(new_role)
                    print("Role updated.")
            elif choice == 6:
                break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    save_data(data)
    print("Staff updated successfully.")