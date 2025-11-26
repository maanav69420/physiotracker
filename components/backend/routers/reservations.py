from typing import Optional
from fastapi import APIRouter, HTTPException, status
from backend.common import load_data  # ensures project root is importable

# reservation helper lives at components/reservation.py
from reservation import create_reservation_for_item, list_reservations, fulfill_reservation

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", summary="List reservations")
def api_list_reservations(status: Optional[str] = None, department: Optional[str] = None):
    """
    List reservations. Optional filters: status (pending/fulfilled/cancelled), department.
    """
    return list_reservations(status=status, department=department)


@router.get("/{res_id}", summary="Get reservation by id")
def api_get_reservation(res_id: int):
    data = load_data()
    reservations = data.get("reservations", [])
    r = next((x for x in reservations if int(x.get("id", 0)) == int(res_id)), None)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return r


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a reservation")
def api_create_reservation(item_id: int, user_email: str, daily_usage: Optional[int] = None, target_amount: Optional[int] = None):
    """
    Create a reservation for an item.
    Query/body params:
      - item_id (int)
      - user_email (str)
      - daily_usage (optional int)
      - target_amount (optional int)
    """
    ok, res = create_reservation_for_item(item_id, user_email, daily_usage=daily_usage, target_amount=target_amount)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/{res_id}/fulfill", summary="Fulfill reservation")
def api_fulfill_reservation(res_id: int):
    ok, out = fulfill_reservation(res_id)
    if not ok:
        raise HTTPException(status_code=400, detail=out)
    return out


@router.delete("/{res_id}", summary="Delete (cancel) reservation")
def api_delete_reservation(res_id: int):
    data = load_data()
    reservations = data.get("reservations", [])
    idx = next((i for i, x in enumerate(reservations) if int(x.get("id", 0)) == int(res_id)), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    # remove reservation
    removed = reservations.pop(idx)
    save_data = None
    try:
        # import save_data from data_store save helper (use backend.common to guarantee imports)
        from data_store import save_data
        save_data(data)
    except Exception:
        # best-effort — if save fails, put back and return error
        reservations.insert(idx, removed)
        raise HTTPException(status_code=500, detail="Failed to persist deletion")
    return {"success": True, "removed": removed}