from email.message import EmailMessage
from data_store import load_data, save_data
import os
import smtplib

# new import
from reservation import create_reservation_for_item, list_reservations

def send_depletion_email(item, data=None):
    if data is None:
        data = load_data()
    admins = list(data.get("admins", {}).items())
    if not admins:
        print("No admin users found — cannot send depletion email.")
        return

    sender = os.environ.get("GET_SENDER")
    password = os.environ.get("GET_PASSKEY")
    if not sender or not password:
        print("Email credentials not found in environment (GET_SENDER / GET_PASSKEY). Skipping email.")
        return

    subject = "URGENT - ITEM STOCK DEPLETED"
    for admin_email, admin_info in admins:
        admin_name = admin_info.get("name", "Admin")
        body = (
            f"{admin_name}, An item require refilling:\n"
            f"Item: {item.get('name')}\n"
            f"Department: {item.get('department')}\n"
            f"Amount Require: {item.get('amount_needed')}\n"
        )
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = admin_email
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(sender, password)
                smtp.send_message(msg)
            print(f"Depletion email sent to {admin_email}.")
        except Exception as e:
            print(f"Failed to send depletion email to {admin_email}: {e}")

def item_used(current_user_email):
    data = load_data()
    staff = data.get("staff", {})
    if not current_user_email or current_user_email not in staff:
        print("Unable to determine your department. Contact admin.")
        return

    dept = staff[current_user_email].get("department")
    if not dept:
        print("Your account has no department set. Contact admin.")
        return

    name_query = input("Enter the name of the item used: ").strip()
    if not name_query:
        print("Item name cannot be empty.")
        return
    matches = [it for it in data.get("items", []) if it.get("department") == dept and it.get("name","").lower() == name_query.lower()]
    if not matches:
        print("Item not found in your department.")
        return
    item = matches[0]
    try:
        used = int(input("Enter amount used (integer): "))
        if used <= 0:
            print("Amount used must be positive.")
            return
    except ValueError:
        print("Invalid amount. Enter an integer.")
        return

    if used >= item.get("current_amount", 0):
        item["current_amount"] = 0
        save_data(data)
        print(f"Used {used}. Current amount for '{item['name']}' is now 0.")
        print(f"Stock for '{item['name']}' is empty — reservation is required.")
        # send email and create automatic reservation
        send_depletion_email(item, data=data)
        ok, res = create_reservation_for_item(item.get("id"), current_user_email)
        if ok:
            print("Reservation created:", res)
        else:
            print("Reservation creation failed:", res)
    else:
        item["current_amount"] = item.get("current_amount", 0) - used
        save_data(data)
        print(f"Used {used}. New current amount for '{item['name']}' is {item['current_amount']}.")

# manage_items remains unchanged (other modules call this)
def manage_items(admin=False, current_user_email=None):
    data = load_data()
    while True:
        print("="*8, " Manage Items ", "="*8)
        print("Current items:")
        if admin:
            items_to_show = data.get("items", [])
        else:
            staff = data.get("staff", {})
            if not current_user_email or current_user_email not in staff:
                print("Unable to determine your department. Contact admin.")
                return
            dept = staff[current_user_email].get("department")
            items_to_show = [it for it in data.get("items", []) if it.get("department") == dept]
        if not items_to_show:
            print("  (no items)")
        else:
            for it in items_to_show:
                print(f'  ID:{it["id"]} | Dept:{it["department"]} | Type:{it["type"]} | Name:{it["name"]} | Needed:{it["amount_needed"]} | Current:{it["current_amount"]}')
        print(
            '''1. Add Item
            2. Remove Item
            3. Update Item
            4. Back'''
        )
        if not admin:
            print("5. Item Used")
            print("6. Refill Item")
            print("7. Reserve Item")
            print("8. View Reservations")
        else:
            print("5. Reserve Items (show depleted items across all departments)")
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                # Add Item
                if admin:
                    print("Available departments:", data.get("departments", []))
                    department = input("Enter department for the item: ").strip()
                    if not department:
                        print("Department cannot be empty.")
                        continue
                    if department not in data.get("departments", []):
                        data.setdefault("departments", []).append(department)
                else:
                    staff = data.get("staff", {})
                    department = staff[current_user_email].get("department")

                itype = input("Is the item consumable or non-consumable? (consumable/non-consumable): ").strip().lower()
                if itype not in ("consumable", "non-consumable"):
                    print("Invalid type. Use 'consumable' or 'non-consumable'.")
                    continue
                name = input("Enter item name: ").strip()
                if not name:
                    print("Name cannot be empty.")
                    continue
                try:
                    amount_needed = int(input("Enter amount needed (integer): "))
                    if amount_needed < 0:
                        print("Amount must be non-negative.")
                        continue
                except ValueError:
                    print("Invalid amount. Enter an integer.")
                    continue
                next_id = max([it.get("id", 0) for it in data.get("items", [])], default=0) + 1
                item = {
                    "id": next_id,
                    "department": department,
                    "type": itype,
                    "name": name,
                    "amount_needed": amount_needed,
                    "current_amount": amount_needed
                }
                data.setdefault("items", []).append(item)
                save_data(data)
                print("Item added successfully.")
            elif choice == 2:
                try:
                    iid = int(input("Enter item ID to remove: "))
                except ValueError:
                    print("Invalid ID.")
                    continue
                found = next((it for it in data.get("items", []) if it["id"] == iid), None)
                if not found:
                    print("Item not found.")
                    continue
                if not admin:
                    staff = data.get("staff", {})
                    if found["department"] != staff[current_user_email].get("department"):
                        print("You cannot remove items from other departments.")
                        continue
                data["items"].remove(found)
                save_data(data)
                print("Item removed.")
            elif choice == 3:
                try:
                    iid = int(input("Enter item ID to update: "))
                except ValueError:
                    print("Invalid ID.")
                    continue
                item = next((it for it in data.get("items", []) if it["id"] == iid), None)
                if not item:
                    print("Item not found.")
                    continue
                if not admin:
                    staff = data.get("staff", {})
                    if item["department"] != staff[current_user_email].get("department"):
                        print("You cannot update items from other departments.")
                        continue
                print("Current item:", item)
                if admin:
                    print("Available departments:", data.get("departments", []))
                    new_dept = input("Enter new department (or press enter to keep): ").strip()
                    if new_dept:
                        item["department"] = new_dept
                        if new_dept not in data.get("departments", []):
                            data.setdefault("departments", []).append(new_dept)
                new_type = input(f"Enter new type (consumable/non-consumable) or press enter to keep [{item['type']}]: ").strip().lower()
                if new_type:
                    if new_type in ("consumable", "non-consumable"):
                        item["type"] = new_type
                    else:
                        print("Invalid type; keeping existing.")
                new_name = input(f"Enter new name or press enter to keep [{item['name']}]: ").strip()
                if new_name:
                    item["name"] = new_name
                try:
                    amt_in = input(f"Enter new amount needed or press enter to keep [{item['amount_needed']}]: ").strip()
                    if amt_in:
                        new_needed = int(amt_in)
                        if new_needed < 0:
                            print("Amount must be non-negative; keeping existing.")
                        else:
                            item["amount_needed"] = new_needed
                            item["current_amount"] = new_needed
                except ValueError:
                    print("Invalid amount input; keeping existing amounts.")
                save_data(data)
                print("Item updated.")
            elif choice == 4:
                break
            elif choice == 5 and admin:
                depleted = [it for it in data.get("items", []) if it.get("current_amount", 0) == 0]
                if not depleted:
                    print("No depleted items across departments.")
                else:
                    print("Depleted items (current_amount == 0):")
                    for it in depleted:
                        print(f'  ID:{it["id"]} | Dept:{it["department"]} | Name:{it["name"]} | Type:{it["type"]} | Needed:{it["amount_needed"]}')
            elif choice == 5 and not admin:
                item_used(current_user_email)
            elif choice == 6 and not admin:
                staff = data.get("staff", {})
                if not current_user_email or current_user_email not in staff:
                    print("Unable to determine your department. Contact admin.")
                    continue
                dept = staff[current_user_email].get("department")
                try:
                    iid = int(input("Enter item ID to refill (must belong to your department): "))
                except ValueError:
                    print("Invalid ID.")
                    continue
                item = next((it for it in data.get("items", []) if it["id"] == iid), None)
                if not item:
                    print("Item not found.")
                    continue
                if item.get("department") != dept:
                    print("You can only refill items in your department.")
                    continue
                item["current_amount"] = item.get("amount_needed", item.get("current_amount", 0))
                save_data(data)
                print(f"Item '{item['name']}' refilled to {item['current_amount']}.")
            elif choice == 7 and not admin:
                # Reserve Item flow for staff
                staff = data.get("staff", {})
                if not current_user_email or current_user_email not in staff:
                    print("Unable to determine your department. Contact admin.")
                    continue
                try:
                    iid = int(input("Enter item ID to reserve (must belong to your department): "))
                except ValueError:
                    print("Invalid ID.")
                    continue
                item = next((it for it in data.get("items", []) if it["id"] == iid), None)
                if not item:
                    print("Item not found.")
                    continue
                if item.get("department") != staff[current_user_email].get("department"):
                    print("You can only reserve items in your department.")
                    continue
                # optional daily usage and target amount
                daily = input("Estimated daily usage (units/day) or press enter to use default heuristic: ").strip()
                target = input("Target amount to refill to (press enter to use amount_needed): ").strip()
                daily_val = int(daily) if daily.isdigit() and int(daily) > 0 else None
                target_val = int(target) if target.isdigit() and int(target) >= 0 else None
                ok, res = create_reservation_for_item(iid, current_user_email, daily_usage=daily_val, target_amount=target_val)
                if ok:
                    print("Reservation created:")
                    print(res)
                else:
                    print("Reservation failed:", res)
            elif choice == 8 and not admin:
                # View reservations for staff's department
                staff = data.get("staff", {})
                if not current_user_email or current_user_email not in staff:
                    print("Unable to determine your department. Contact admin.")
                    continue
                dept = staff[current_user_email].get("department")
                res_list = list_reservations(department=dept)
                if not res_list:
                    print("No reservations for your department.")
                else:
                    print("Reservations:")
                    for r in res_list:
                        print(f'  ID:{r["id"]} | ItemID:{r["item_id"]} | Item:{r["item_name"]} | User:{r["user_email"]} | Expected Restock:{r["expected_restock_date"]} | Status:{r["status"]}')
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")