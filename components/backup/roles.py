from data_store import load_data, save_data

def manage_roles():
    data = load_data()
    while True:
        print("="*8, " Manage Roles ", "="*8)
        print("Current roles:", data["roles"])
        print(
            '''1. Add Role
            2. Remove Role
            3. Update Role
            4. Back'''
        )
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                role = input("Enter role name: ")
                if role not in data["roles"]:
                    data["roles"].append(role)
                    save_data(data)
                    print("Role added successfully.")
                else:
                    print("Role already exists.")
            elif choice == 2:
                role = input("Enter role name to remove: ")
                if role in data["roles"]:
                    data["roles"].remove(role)
                    save_data(data)
                    print("Role removed successfully.")
                else:
                    print("Role not found.")
            elif choice == 3:
                old_role = input("Enter current role name: ")
                if old_role in data["roles"]:
                    new_role = input("Enter new role name: ")
                    index = data["roles"].index(old_role)
                    data["roles"][index] = new_role
                    save_data(data)
                    print("Role updated successfully.")
                else:
                    print("Role not found.")
            elif choice == 4:
                break
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")