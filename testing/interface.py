# interface.py
import database


def Home(db, cursor):
    while True:
        print("\n" + "-"*10 + " Welcome to our portal " + "-"*10)
        print("1. Admin access\n2. Staff access\n3. Exit")
        choice = int(input("Enter your choice: "))

        if choice == 1:
            admin_access(db, cursor)
        elif choice == 2:
            staff_access(db, cursor)
        elif choice == 3:
            break
        else:
            print("Invalid choice.")


# ================= ADMIN ACCESS =================
def admin_access(db, cursor):
    while True:
        print("\n" + "-"*10 + " Admin Access " + "-"*10)
        print("1. Login\n2. Register as Admin\n3. Exit")
        choice = int(input("Enter choice: "))

        if choice == 1:
            email, pswd = take_info()
            if database.login_admin(cursor, email, pswd):
                admin_menu(db, cursor)
            else:
                print("❌ Invalid credentials.")
        elif choice == 2:
            database.register_admin(db, cursor)
        elif choice == 3:
            return
        else:
            print("Invalid choice.")


# ================= STAFF ACCESS =================
def staff_access(db, cursor):
    while True:
        print("\n" + "-"*10 + " Staff Access " + "-"*10)
        print("1. Login\n2. Register as Staff\n3. Exit")
        choice = int(input("Enter choice: "))

        if choice == 1:
            email, pswd = take_info()
            if database.login_staff(cursor, email, pswd):
                staff_menu(email)
            else:
                print("❌ Invalid credentials.")
        elif choice == 2:
            database.register_staff(db, cursor)
        elif choice == 3:
            return
        else:
            print("Invalid choice.")


# ================= ADMIN MENU =================
def admin_menu(db, cursor):
    while True:
        print("\n" + "-"*10 + " Admin Operations " + "-"*10)
        print("1. Update staff department\n2. Update staff role\n3. Delete staff\n4. Display staff\n5. Exit")
        choice = int(input("Enter choice: "))

        if choice == 1:
            email = input("Enter staff email: ")
            dept = input("Enter new department: ")
            database.update_staff_department(db, cursor, email, dept)
        elif choice == 2:
            email = input("Enter staff email: ")
            role = input("Enter new role: ")
            database.update_staff_role(db, cursor, email, role)
        elif choice == 3:
            email = input("Enter staff email to delete: ")
            database.delete_staff(db, cursor, email)
        elif choice == 4:
            rows = database.display_staff(cursor)
            print("\n--- Staff List ---")
            for row in rows:
                print(row)
        elif choice == 5:
            break
        else:
            print("Invalid choice.")


# ================= STAFF MENU =================
def staff_menu(email):
    print(f"\n✅ Welcome Staff: {email}")
    print("You have limited access.\n")


# ================= HELPERS =================
def take_info():
    email = input("Enter your EmailID: ")
    pswd = input("Enter your Password: ")
    return email, pswd


# ================= START APP =================
if __name__ == "__main__":
    db, cursor = database.init_db()
    Home(db, cursor)
