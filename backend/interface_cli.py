import json
import os
import smtplib
from email.message import EmailMessage
from auth import register_user, login_user
from items import manage_items, send_depletion_email
from staff import manage_staff
from roles import manage_roles
from departments import manage_departments
from data_store import load_data as ds_load_data, save_data as ds_save_data

DATA_FILE = "data.json"
DEFAULT_ROLES_FILE = "default_roles.json"

# Load default roles from JSON file
def load_default_roles():
    if os.path.exists(DEFAULT_ROLES_FILE):
        with open(DEFAULT_ROLES_FILE, "r") as file:
            return json.load(file)
    return []

# replace local JSON load/save with wrappers that use data_store but keep defaults
def load_data():
    data = ds_load_data()
    # ensure default roles from file are present
    default_roles = load_default_roles()
    for role in default_roles:
        if role not in data.get("roles", []):
            data.setdefault("roles", []).append(role)
    # ensure "Head" and "Office" are present
    if "Head" not in data.get("roles", []):
        data.setdefault("roles", []).append("Head")
    if "Office" not in data.get("departments", []):
        data.setdefault("departments", []).append("Office")
    if "items" not in data:
        data["items"] = []
    return data

def save_data(data):
    # delegate to data_store; data_store will fallback to JSON if no Mongo
    ds_save_data(data)

# Admin dashboard
def admin_dashboard(logged_in_email):
    while True:
        # Refresh data each loop so notification is up-to-date
        data = load_data()
        depleted = [it for it in data.get("items", []) if it.get("current_amount", 0) == 0]
        if depleted:
            print("="*8, " REFILL NOTICE ", "="*8)
            print(f"⚠️  {len(depleted)} item(s) need refilling:")
            for it in depleted:
                # show brief info for each depleted item
                print(f'  ID:{it.get("id")} | Dept:{it.get("department")} | Name:{it.get("name")}')
            print("-"*40)

        print("="*8, " Admin Dashboard ", "="*8)
        print(
            '''1. Manage Staff
            2. Manage Items
            3. Manage Roles
            4. Manage Departments
            5. Logout'''
        )
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                manage_staff(admin=True)
            elif choice == 2:
                manage_items(admin=True, current_user_email=logged_in_email)
            elif choice == 3:
                manage_roles()
            elif choice == 4:
                manage_departments()
            elif choice == 5:
                print("Logging out...")
                break
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# Staff dashboard
def staff_dashboard(logged_in_email):
    while True:
        print("="*8, " Staff Dashboard ", "="*8)
        print(
            '''1. Manage Staff
            2. Manage Items
            3. Manage Roles
            4. Manage Departments
            5. Logout'''
        )
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                manage_staff(admin=False)
            elif choice == 2:
                manage_items(admin=False, current_user_email=logged_in_email)
            elif choice == 3:
                manage_roles()
            elif choice == 4:
                manage_departments()
            elif choice == 5:
                print("Logging out...")
                break
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def home():
    print("="*8 , " Home Page " , "="*8)
    print(
        '''1. Access as Admin
        2. Access as Staff
        3. Exit'''
        )
    while True:
        try:
            choice = int(input("enter your choice:\t"))
            if choice == 1:
                admin_menu()
            elif choice == 2:
                staff_menu()
            elif choice == 3:
                print("Exiting the program")
                print("Thank you for using our program")
                print("-"*8)
                break
            else:
                print("Invalid choice , please try again")
        except ValueError:
            print("Invalid input. Please enter a number.")

def admin_menu():
    print("="*8 , " Admin Menu " , "="*8)
    while True:
        print(
            '''1. Register
        2. Login
        3. Back to Home Page'''
        )
        try:
            choice = int(input("enter your choice:\t"))
            if choice == 1:
                register_user("Admin")
                # return to admin menu after registration
                continue
            elif choice == 2:
                success, email = login_user("Admin")
                if success:
                    admin_dashboard(email)
                # after logout or failed login, show admin menu again
                continue
            elif choice == 3:
                # go back to home
                return
            else:
                print("Invalid choice , please try again")
        except ValueError:
            print("Invalid input. Please enter a number.")

def staff_menu():
    print("="*8 , " Staff Menu " , "="*8)
    while True:
        print(
            '''1. Register
        2. Login
        3. Back to Home Page'''
        )
        try:
            choice = int(input("enter your choice:\t"))
            if choice == 1:
                register_user("Staff")
                # return to staff menu after registration
                continue
            elif choice == 2:
                success, email = login_user("Staff")
                if success:
                    staff_dashboard(email)
                # after logout or failed login, show staff menu again
                continue
            elif choice == 3:
                # go back to home
                return
            else:
                print("Invalid choice , please try again")
        except ValueError:
            print("Invalid input. Please enter a number.")

# Start the program
if __name__ == "__main__":
    home()
