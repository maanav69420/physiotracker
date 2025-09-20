import database


def Home(db, cursor):
    while True:
        print()
        print(f'{"-"*10} Welcome to our portal {"-"*10}')
        print(
            '''Choose your options
            1. Admin access
            2. Staff access
            3. Exit'''
        )
        
        counter = int(input("Enter your choice: "))
        if counter == 1:
            admin_access(db, cursor)
        elif counter == 2:
            staff_access(db, cursor)
        elif counter == 3:
            break 
        else:
            print("Invalid Command") 


def admin_access(db, cursor):
    while True:
        print()
        print(f'{"-"*10} Admin Access {"-"*10}')
        print("1. Enter your details\n2. Exit")
        counter = int(input("Enter choice: "))
        if counter == 1:    
            mail , pswd = take_info()
            if database.validate_admin(cursor, mail):
                admin_menu(db, cursor)
            else:
                print("Access Denied: Not an admin.")
        if counter == 2:    
            return                
        else:   
            print("Invalid Command")


def staff_access(db, cursor):
    while True:
        print()
        print(f'{"-"*10} Staff Access {"-"*10}')
        print("1. Enter your details\n2. Exit")
        counter = int(input("Enter choice: "))
        if counter == 1:    
            mail , pswd = take_info()
            if database.validate_staff(cursor, mail):
                staff_menu(db, cursor, mail)
            else:
                print("Access Denied: Invalid staff info.")
        if counter == 2:    
            return                
        else:   
            print("Invalid Command")


def take_info():
    email = str(input("Enter your EmailID:\t"))
    pswd = str(input("Enter your Password:\t"))
    return email , pswd


# ================= ADMIN MENU =================
def admin_menu(db, cursor):
    while True:
        print(f'{"-"*10} Admin Operations {"-"*10}')
        print('''
            1. Add record
            2. Update record
            3. Delete record
            4. Display all staff
            5. Exit
        ''')
        choice = int(input("Enter choice: "))

        if choice == 1:
            table = input("Enter table name (info/department/role): ")
            if table == "info":
                name = input("Name: "); email = input("Email: ")
                database.add_record(db, cursor, table, (name, email))
            elif table == "department":
                name = input("Name: "); dept = input("Department: ")
                database.add_record(db, cursor, table, (name, dept))
            elif table == "role":
                name = input("Name: "); rolw = input("Role: ")
                database.add_record(db, cursor, table, (name, rolw))

        elif choice == 2:
            table = input("Enter table (info/department/role): ")
            name = input("Name to update: ")
            new_value = input("New value: ")
            database.update_record(db, cursor, table, name, new_value)

        elif choice == 3:
            table = input("Enter table (info/department/role): ")
            name = input("Name to delete: ")
            database.delete_record(db, cursor, table, name)

        elif choice == 4:
            rows = database.display_staff(cursor)
            for row in rows:
                print(row)

        elif choice == 5:
            break
        else:
            print("Invalid choice.")


# ================= STAFF MENU =================
def staff_menu(db, cursor, email):
    result = database.get_staff_info(cursor, email)
    if not result:
        print("No department/role assigned.")
        return
    dept, rolw = result

    while True:
        print(f'{"-"*10} Staff Operations {"-"*10}')
        print("1. View my items\n2. Add item\n3. Delete item\n4. Exit")
        choice = int(input("Enter choice: "))

        if choice == 1:
            rows = database.get_items(cursor, dept, rolw)
            for row in rows:
                print(row)

        elif choice == 2:
            print("\nAvailable items in database:")
            items = database.list_all_items(cursor)
            if items:
                for i, it in enumerate(items, 1):
                    print(f"{i}. {it}")
            else:
                print("No items exist yet. You may create a new one.")

            item = input("Enter item name (choose existing or type new): ").strip()
            qty = int(input("Enter quantity (max 10): "))

            database.add_or_update_item(db, cursor, dept, rolw, item, qty)

        elif choice == 3:
            item = input("Enter item to delete: ")
            database.delete_item(db, cursor, dept, rolw, item)

        elif choice == 4:
            break
        else:
            print("Invalid choice.")


# ================= START APP =================
if __name__ == "__main__":
    db, cursor = database.init_db()
    Home(db, cursor)
