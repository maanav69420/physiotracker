from datetime import date, timedelta
import math
from data_store import load_data, save_data

# new imports for email
import os
import smtplib
from email.message import EmailMessage

def _default_daily_usage(item):
    """
    Estimate a default daily usage if no real usage metric is available.
    Use amount_needed/7 (one-week turnover) rounded up, at least 1.
    """
    amt = item.get("amount_needed", 0) or 0
    est = max(1, math.ceil(amt / 7)) if amt > 0 else 1
    return est

def estimate_depletion_date(item, daily_usage=None):
    """
    Estimate the date when current_amount will reach zero.
    item: dict with keys 'current_amount' (int)
    daily_usage: optional int (units/day). If None, a heuristic is used.
    Returns a date object (today if already depleted).
    """
    today = date.today()
    current = int(item.get("current_amount", 0) or 0)
    if current <= 0:
        return today
    rate = int(daily_usage) if daily_usage and int(daily_usage) > 0 else _default_daily_usage(item)
    days = math.ceil(current / rate)
    return today + timedelta(days=days)

def estimate_refill_date_to_target(item, target_amount=None, daily_usage=None):
    """
    Estimate when a refill to reach target_amount will be required.
    target_amount defaults to item['amount_needed'] if not provided.
    Returns date object when current_amount will fall below target (i.e., when refill needed),
    and amount_to_refill (target - current if positive).
    """
    today = date.today()
    target = int(target_amount) if target_amount is not None else int(item.get("amount_needed", 0) or 0)
    current = int(item.get("current_amount", 0) or 0)
    if current >= target:
        # Enough stock for now; compute depletion date instead
        return estimate_depletion_date(item, daily_usage), max(0, target - current)
    # amount short now -> needs refill immediately
    return today, max(0, target - current)

def _next_reservation_id(data):
    res = data.get("reservations", [])
    if not res:
        return 1
    return max(r.get("id", 0) for r in res) + 1

def _send_reservation_email(reservation, data=None):
    """
    Send email to all admins notifying about the reservation.
    Message: "This is to inform you that [item name] has been reserved by [staff name] from [department name] during the time period of [time intervals in days] days"
    Subject: "Item Reservation"
    """
    if data is None:
        data = load_data()
    admins = list(data.get("admins", {}).items())
    if not admins:
        # no admins configured
        return
    sender = os.environ.get("GET_SENDER")
    password = os.environ.get("GET_PASSKEY")
    if not sender or not password:
        print("reservation: email credentials GET_SENDER/GET_PASSKEY not set; skipping reservation email")
        return

    item_name = reservation.get("item_name", "Unknown item")
    dept = reservation.get("department", "Unknown department")
    staff_email = reservation.get("user_email", "")
    staff_name = data.get("staff", {}).get(staff_email, {}).get("name", staff_email or "Unknown staff")
    # compute days interval
    try:
        expected = date.fromisoformat(reservation.get("expected_restock_date"))
        created = date.fromisoformat(reservation.get("created_on"))
        days = (expected - created).days
        if days < 0:
            days = 0
    except Exception:
        days = 0

    subject = "Item Reservation"
    body = f"This is to inform you that {item_name} has been reserved by {staff_name} from {dept} during the time period of {days} days"

    msg = EmailMessage()
    msg["From"] = sender
    msg["Subject"] = subject
    msg.set_content(body)

    # send to each admin; continue on failures
    for admin_email, _info in admins:
        msg["To"] = admin_email
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(sender, password)
                smtp.send_message(msg)
            # clear To header for next recipient
            del msg["To"]
        except Exception as e:
            print(f"reservation: failed to send email to {admin_email}: {e}")
            try:
                del msg["To"]
            except Exception:
                pass

def create_reservation_for_item(item_id, user_email, daily_usage=None, target_amount=None):
    """
    Create a reservation record for an item.
    - Finds item by id
    - Computes expected_restock_date (when current_amount depletes) using daily_usage or heuristic
    - Computes amount_to_refill = max(0, target_amount - current_amount) where target_amount defaults to amount_needed
    - Saves reservation into data['reservations']
    Returns (True, reservation_dict) on success, (False, message) on failure.
    """
    data = load_data()
    items = data.get("items", [])
    item = next((it for it in items if int(it.get("id", 0)) == int(item_id)), None)
    if item is None:
        return False, f"Item id {item_id} not found."

    # estimate depletion
    depletion_date = estimate_depletion_date(item, daily_usage)
    # estimate amount to refill to reach target
    target = int(target_amount) if target_amount is not None else int(item.get("amount_needed", 0) or 0)
    current = int(item.get("current_amount", 0) or 0)
    amount_to_refill = max(0, target - current)

    reservation = {
        "id": _next_reservation_id(data),
        "item_id": int(item_id),
        "item_name": item.get("name"),
        "department": item.get("department"),
        "user_email": user_email,
        "created_on": date.today().isoformat(),
        "expected_restock_date": depletion_date.isoformat(),
        "amount_to_refill": amount_to_refill,
        "status": "pending"  # pending / fulfilled / cancelled
    }

    data.setdefault("reservations", []).append(reservation)
    save_data(data)

    # send notification email to admins (best-effort)
    try:
        _send_reservation_email(reservation, data=data)
    except Exception as e:
        print("reservation: unexpected error sending reservation email:", e)

    return True, reservation

def list_reservations(status=None, department=None):
    """
    Return list of reservations, optionally filtered by status or department.
    """
    data = load_data()
    res = data.get("reservations", [])
    if status:
        res = [r for r in res if r.get("status") == status]
    if department:
        res = [r for r in res if r.get("department") == department]
    return res

def fulfill_reservation(reservation_id):
    """
    Mark a reservation as fulfilled and (optionally) update item current_amount to amount_needed.
    Returns (True, reservation) or (False, message).
    """
    data = load_data()
    res_list = data.get("reservations", [])
    r = next((x for x in res_list if x.get("id", int(reservation_id))), None)
    if not r:
        return False, "Reservation not found."
    if r.get("status") != "pending":
        return False, "Reservation not pending."
    # find item and refill to amount_needed
    item = next((it for it in data.get("items", []) if int(it.get("id", 0)) == int(r.get("item_id"))), None)
    if item:
        item["current_amount"] = int(item.get("amount_needed", item.get("current_amount", 0)) or 0)
    r["status"] = "fulfilled"
    r["fulfilled_on"] = date.today().isoformat()
    save_data(data)
    return True, r