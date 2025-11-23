from email.message import EmailMessage
from data_store import load_data, save_data
import os
import smtplib

def send_depletion_email(item, data=None):
    if data is None:
        data = load_data()
    admins = [(email, info) for email, info in data.get("users", {}).items() if info.get("type") == "admin"]
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
    if not current_user_email or current_user_email not in data["users"]:
        print("Unable to determine your department. Contact admin.")
        return
    dept = data["users"][current_user_email]["department"]
    name_query = input("Enter the name of the item used: ").strip()
    if not name_query:
        print("Item name cannot be empty.")
        return
    matches = [it for it in data["items"] if it.get("department") == dept and it.get("name","").lower() == name_query.lower()]
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

    if used >= item["current_amount"]:
        item["current_amount"] = 0
        save_data(data)
        print(f"Used {used}. Current amount for '{item['name']}' is now 0.")
        print(f"Stock for '{item['name']}' is empty — reservation is required.")
        send_depletion_email(item, data=data)
    else:
        item["current_amount"] = item["current_amount"] - used
        save_data(data)
        print(f"Used {used}. New current amount for '{item['name']}' is {item['current_amount']}.")

# manage_items remains unchanged (other modules call this)
def manage_items(admin=False, current_user_email=None):
    data = load_data()
    while True:
        print("="*8, " Manage Items ", "="*8)
        print("Current items:")
        if admin:
            items_to_show = data["items"]
        else:
            if not current_user_email or current_user_email not in data["users"]:
                print("Unable to determine your department. Contact admin.")
                return
            dept = data["users"][current_user_email]["department"]
            items_to_show = [it for it in data["items"] if it.get("department") == dept]
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
        else:
            print("5. Reserve Items (show depleted items across all departments)")
        try:
            choice = int(input("Enter your choice: "))
            if choice == 1:
                # Add Item
                if admin:
                    print("Available departments:", data["departments"])
                    department = input("Enter department for the item: ").strip()
                    if not department:
                        print("Department cannot be empty.")
                        continue
                    if department not in data["departments"]:
                        data["departments"].append(department)
                else:
                    department = data["users"][current_user_email]["department"]

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
                next_id = max([it.get("id", 0) for it in data["items"]], default=0) + 1
                item = {
                    "id": next_id,
                    "department": department,
                    "type": itype,
                    "name": name,
                    "amount_needed": amount_needed,
                    "current_amount": amount_needed
                }
                data["items"].append(item)
                save_data(data)
                print("Item added successfully.")
            elif choice == 2:
                try:
                    iid = int(input("Enter item ID to remove: "))
                except ValueError:
                    print("Invalid ID.")
                    continue
                found = next((it for it in data["items"] if it["id"] == iid), None)
                if not found:
                    print("Item not found.")
                    continue
                if not admin and found["department"] != data["users"][current_user_email]["department"]:
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
                item = next((it for it in data["items"] if it["id"] == iid), None)
                if not item:
                    print("Item not found.")
                    continue
                if not admin and item["department"] != data["users"][current_user_email]["department"]:
                    print("You cannot update items from other departments.")
                    continue
                print("Current item:", item)
                if admin:
                    print("Available departments:", data["departments"])
                    new_dept = input("Enter new department (or press enter to keep): ").strip()
                    if new_dept:
                        item["department"] = new_dept
                        if new_dept not in data["departments"]:
                            data["departments"].append(new_dept)
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
                depleted = [it for it in data["items"] if it.get("current_amount", 0) == 0]
                if not depleted:
                    print("No depleted items across departments.")
                else:
                    print("Depleted items (current_amount == 0):")
                    for it in depleted:
                        print(f'  ID:{it["id"]} | Dept:{it["department"]} | Name:{it["name"]} | Type:{it["type"]} | Needed:{it["amount_needed"]}')
            elif choice == 5 and not admin:
                item_used(current_user_email)
            elif choice == 6 and not admin:
                if not current_user_email or current_user_email not in data["users"]:
                    print("Unable to determine your department. Contact admin.")
                    continue
                dept = data["users"][current_user_email]["department"]
                try:
                    iid = int(input("Enter item ID to refill (must belong to your department): "))
                except ValueError:
                    print("Invalid ID.")
                    continue
                item = next((it for it in data["items"] if it["id"] == iid), None)
                if not item:
                    print("Item not found.")
                    continue
                if item.get("department") != dept:
                    print("You can only refill items in your department.")
                    continue
                item["current_amount"] = item.get("amount_needed", item.get("current_amount", 0))
                save_data(data)
                print(f"Item '{item['name']}' refilled to {item['current_amount']}.")
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")