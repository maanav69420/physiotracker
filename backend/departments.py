from data_store import load_data, save_data

def manage_departments():
    data = load_data()
    while True:
        print("="*8, " Manage Departments ", "="*8)
        print("Current departments:", data["departments"])
        print(
            '''1. Add Department
            2. Remove Department
            3. Update Department
            4. Back'''
        )
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                dept = input("Enter department name: ")
                if dept not in data["departments"]:
                    data["departments"].append(dept)
                    save_data(data)
                    print("Department added successfully.")
                else:
                    print("Department already exists.")
            elif choice == 2:
                dept = input("Enter department name to remove: ")
                if dept in data["departments"]:
                    data["departments"].remove(dept)
                    save_data(data)
                    print("Department removed successfully.")
                else:
                    print("Department not found.")
            elif choice == 3:
                old_dept = input("Enter current department name: ")
                if old_dept in data["departments"]:
                    new_dept = input("Enter new department name: ")
                    index = data["departments"].index(old_dept)
                    data["departments"][index] = new_dept
                    save_data(data)
                    print("Department updated successfully.")
                else:
                    print("Department not found.")
            elif choice == 4:
                break
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")