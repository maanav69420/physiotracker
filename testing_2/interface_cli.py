# interface.py
import os
import json
from database import (
    create_tables,
    sync_database_with_json,
    get_departments,
    get_roles,
    add_staff_with_role_dept,
    remove_staff_by_email,
    update_staff_name_email,
    update_staff_role_dept,
    get_all_staff,
    find_staff_by_name_email,
    add_item,
    remove_item,
    update_item_quantity,
    update_json_from_db,
)

# ---------- Helper ----------
def choose_from_list(options, label="option"):
    if not options:
        print("⚠️ No options available.")
        return None
    for i, (k, name) in enumerate(options, start=1):
        print(f"{i}. {name} (id: {k})")
    while True:
        choice = input(f"Choose {label} (number or 'back'): ").strip()
        if choice.lower() == "back":
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("⚠️ Invalid choice, try again.")


# ---------- Manage Staff ----------
def manage_staff_menu():
    while True:
        print("\n--- Manage Staff ---")
        print("1. Add Staff")
        print("2. Remove Staff")
        print("3. Update Staff")
        print("4. View All Staff")
        print("5. Back")
        choice = input("Enter choice: ").strip()
        if choice == "1":
            add_staff_cli()
        elif choice == "2":
            remove_staff_cli()
        elif choice == "3":
            update_staff_cli()
        elif choice == "4":
            view_staff_cli()
        elif choice == "5":
            break
        else:
            print("⚠️ Invalid option.")


def add_staff_cli():
    print("\n--- Add Staff ---")
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()
    roles = get_roles()
    chosen_role = choose_from_list(roles, "role")
    if not chosen_role:
        print("Cancelled.")
        return
    departments = get_departments()
    chosen_dept = choose_from_list(departments, "department")
    if not chosen_dept:
        print("Cancelled.")
        return

    confirm = input(f"Confirm adding staff '{full_name}' with role '{chosen_role[1]}' in '{chosen_dept[1]}'? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Addition cancelled.")
        return

    role_name = chosen_role[1]
    dept_name = chosen_dept[1]
    ok, msg = add_staff_with_role_dept(full_name, email, role_name, dept_name)
    print(("✅ " if ok else "❌ ") + msg)


def remove_staff_cli():
    print("\n--- Remove Staff ---")
    staff = get_all_staff()
    if not staff:
        print("⚠️ No staff to remove.")
        return
    for i, s in enumerate(staff, start=1):
        name = f"{s['first_name']} {s['second_name'] or ''}".strip()
        print(f"{i}. {name} | {s['email']} | {s['role'] or 'no-role'} | {s['department'] or 'no-dept'}")

    choice = input("Enter email of staff to remove (or 'back'): ").strip()
    if choice.lower() == "back":
        return

    confirm = input(f"⚠️ Are you sure you want to delete staff with email '{choice}'? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Deletion cancelled.")
        return

    ok, msg = remove_staff_by_email(choice)
    print(("✅ " if ok else "❌ ") + msg)


def update_staff_cli():
    print("\n--- Update Staff ---")
    email = input("Enter staff email to update (or 'back'): ").strip()
    if email.lower() == "back":
        return
    staff_row = next((s for s in get_all_staff() if s["email"] == email), None)
    if not staff_row:
        print("❌ Staff not found.")
        return

    print("What to update?")
    print("1. Name")
    print("2. Email")
    print("3. Role")
    print("4. Department")
    print("5. Back")
    choice = input("Enter choice: ").strip()

    if choice == "1":
        new_name = input("Enter new full name: ").strip()
        confirm = input(f"⚠️ Confirm changing name to '{new_name}'? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Update cancelled.")
            return
        ok, msg = update_staff_name_email(email, new_full_name=new_name)
        print(("✅ " if ok else "❌ ") + msg)

    elif choice == "2":
        new_email = input("Enter new email: ").strip()
        confirm = input(f"⚠️ Confirm changing email to '{new_email}'? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Update cancelled.")
            return
        ok, msg = update_staff_name_email(email, new_email=new_email)
        print(("✅ " if ok else "❌ ") + msg)

    elif choice == "3":
        roles = get_roles()
        chosen_role = choose_from_list(roles, "role")
        if not chosen_role:
            print("Cancelled.")
            return
        confirm = input(f"⚠️ Confirm changing role to '{chosen_role[1]}'? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Update cancelled.")
            return
        ok, msg = update_staff_role_dept(email, new_role=chosen_role[1])
        print(("✅ " if ok else "❌ ") + msg)

    elif choice == "4":
        depts = get_departments()
        chosen_dept = choose_from_list(depts, "department")
        if not chosen_dept:
            print("Cancelled.")
            return
        confirm = input(f"⚠️ Confirm changing department to '{chosen_dept[1]}'? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Update cancelled.")
            return
        ok, msg = update_staff_role_dept(email, new_dept=chosen_dept[1])
        print(("✅ " if ok else "❌ ") + msg)

    elif choice == "5":
        return
    else:
        print("⚠️ Invalid choice.")


def view_staff_cli():
    rows = get_all_staff()
    if not rows:
        print("⚠️ No staff found.")
        return
    print("\n--- Staff List ---")
    for s in rows:
        name = f"{s['first_name']} {s['second_name'] or ''}".strip()
        print(f"- {name} | {s['email']} | role: {s['role'] or '-'} | dept: {s['department'] or '-'}")


# ---------- Admin ----------
def admin_menu():
    while True:
        print("\n=== Admin Menu ===")
        print("1. Manage Items")
        print("2. Manage Staff")
        print("3. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            admin_manage_items()
        elif ch == "2":
            manage_staff_menu()
        elif ch == "3":
            break
        else:
            print("⚠️ Invalid choice.")


def admin_manage_items():
    while True:
        print("\n--- Admin: Manage Items ---")
        print("1. Add Item")
        print("2. Remove Item")
        print("3. Update Item Quantity")
        print("4. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            depts = get_departments()
            sel = choose_from_list(depts, "department")
            if not sel:
                continue
            dept_key = sel[0]
            item = input("Item name: ").strip()
            default_q = input("Default quantity (int): ").strip()
            current_q = input("Current quantity (int): ").strip()
            confirm = input(f"Confirm adding item '{item}' with default={default_q}, current={current_q}? (y/n): ").strip().lower()
            if confirm != "y":
                print("❌ Addition cancelled.")
                continue
            add_item(dept_key, item, int(default_q), int(current_q))
            print("✅ Item added.")
        elif ch == "2":
            item = input("Item name to remove: ").strip()
            confirm = input(f"⚠️ Are you sure you want to delete '{item}'? (y/n): ").strip().lower()
            if confirm == "y":
                remove_item(item)
                print("✅ Item removed (if existed).")
            else:
                print("❌ Deletion cancelled.")
        elif ch == "3":
            item = input("Item name: ").strip()
            qty = input("New current quantity: ").strip()
            confirm = input(f"⚠️ Confirm updating '{item}' quantity to {qty}? (y/n): ").strip().lower()
            if confirm != "y":
                print("❌ Update cancelled.")
                continue
            update_item_quantity(item, int(qty))
            print("✅ Quantity updated.")
        elif ch == "4":
            break
        else:
            print("⚠️ Invalid choice.")


# ---------- Staff ----------
def staff_menu():
    print("\n--- Staff Login ---")
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()
    user = find_staff_by_name_email(full_name, email)
    if not user:
        print("❌ Invalid credentials.")
        return

    staff_row = next((s for s in get_all_staff() if s["email"] == email), None)
    if not staff_row:
        print("❌ Could not find staff mapping.")
        return
    dept_name = staff_row["department"]
    if not dept_name:
        print("⚠️ You are not assigned to a department.")
        return

    depts = get_departments()
    dept_key = next((k for (k, n) in depts if n == dept_name), None)

    while True:
        print(f"\n--- Staff Operations (Department: {dept_name}) ---")
        print("1. Add Item")
        print("2. Update Item Quantity")
        print("3. Remove Item")
        print("4. View Items")
        print("5. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            item = input("Item name: ").strip()
            default_q = input("Default qty: ").strip()
            current_q = input("Current qty: ").strip()
            confirm = input(f"Confirm adding '{item}' with default={default_q}, current={current_q}? (y/n): ").strip().lower()
            if confirm != "y":
                print("❌ Addition cancelled.")
                continue
            add_item(dept_key, item, int(default_q), int(current_q))
            print("✅ Item added.")
        elif ch == "2":
            item = input("Item name: ").strip()
            qty = input("New qty: ").strip()
            confirm = input(f"⚠️ Confirm updating '{item}' quantity to {qty}? (y/n): ").strip().lower()
            if confirm != "y":
                print("❌ Update cancelled.")
                continue
            update_item_quantity(item, int(qty), dept_key)
            print("✅ Quantity updated.")
        elif ch == "3":
            item = input("Item name: ").strip()
            confirm = input(f"⚠️ Are you sure you want to delete '{item}' from {dept_name}? (y/n): ").strip().lower()
            if confirm == "y":
                remove_item(item, dept_key)
                print("✅ Item removed.")
            else:
                print("❌ Deletion cancelled.")
        elif ch == "4":
            update_json_from_db()
            path = os.path.join("info", "departments", f"{dept_key}.json")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"\nItems for {dept_name}:")
                for iname, q in data.get(dept_name, {}).items():
                    print(f"- {iname} | default: {q.get('default', 0)} | current: {q.get('current', 0)}")
            else:
                print("⚠️ No items found.")
        elif ch == "5":
            break
        else:
            print("⚠️ Invalid choice.")


# ---------- Main ----------
def main():
    create_tables()
    sync_database_with_json()
    while True:
        print("\n=== Inventory Manager ===")
        print("1. Admin")
        print("2. Staff")
        print("3. Exit")
        choice = input("Enter choice: ").strip()
        if choice == "1":
            admin_menu()
        elif choice == "2":
            staff_menu()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("⚠️ Invalid choice.")


if __name__ == "__main__":
    main()
