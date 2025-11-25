from flask import Flask, render_template, send_from_directory, request
from flask_restx import Api, Resource, fields
import os
from inventory import MongoInventoryManager
from functools import wraps

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)
app.secret_key = 'demo-secret-key'

api = Api(
    app,
    version='1.0',
    title='PhysioTracker API',
    description='Inventory & Staff Management API',
    doc='/api/docs/',
    prefix='/api'
)

class PatchedMongoInventoryManager(MongoInventoryManager):
    def request_item(self, item_id, data):
        return {
            'success': True,
            'item_id': item_id,
            'data': data,
            'message': 'Item request processed (placeholder implementation)'
        }

    def return_item(self, item_id, data):
        return {
            'success': True,
            'item_id': item_id,
            'data': data,
            'message': 'Item return processed (placeholder implementation)'
        }

inventory_manager = PatchedMongoInventoryManager()

# ---------- Models ----------
staff_model = api.model('Staff', {
    'name': fields.String(required=True),
    'email': fields.String(required=True),
    'department': fields.String(required=True),
    'role': fields.String(required=True),
    'phone': fields.String,
    'password': fields.String
})

item_model = api.model('Item', {
    'id': fields.String(required=True, description='Unique item ID'),
    'name': fields.String(required=True),
    'description': fields.String,
    'department': fields.String(required=True),
    'quantity': fields.Integer(required=True),
    'min_stock_level': fields.Integer,
    'location': fields.String(required=True),
    'supplier': fields.String
})

# NEW: request body models for endpoints that were showing "No parameters"
auth_model = api.model('Auth', {
    'email': fields.String(required=True),
    'password': fields.String(required=True),
})

admin_add_staff_model = api.clone('AdminAddStaff', staff_model, {
    'admin_user_id': fields.Integer(required=True, description='Existing admin user_id'),
})

reservation_schedule_model = api.model('ScheduleReservation', {
    'user_id': fields.Integer(required=True),
    'user_name': fields.String(required=True),
    'start_datetime': fields.String(required=True, description='ISO start (e.g. 2025-11-24T14:00:00)'),
    'end_datetime': fields.String(required=True, description='ISO end'),
    'notes': fields.String
})

cancel_reservation_model = api.model('CancelReservation', {
    'user_id': fields.Integer(description='User ID of requester'),
    'admin_user_id': fields.Integer(description='Admin ID (if admin cancelling)')
})

staff_ns = api.namespace('staff', description='Staff Management')
items_ns = api.namespace('items', description='Inventory Management')
utils_ns = api.namespace('utils', description='Utility')

# ---------- Helpers ----------
def respond(result, ok_code=200):
    if isinstance(result, dict) and not result.get('success', True):
        return result, result.get('code', 400)
    return result, ok_code

def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {'success': False, 'message': f'Server error: {e}'}, 500

def require_admin_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json() or {}
        admin_id = data.get('admin_user_id')
        if not admin_id:
            return {'success': False, 'message': 'Admin user ID required'}, 401
        perm = inventory_manager.check_admin_permission(admin_id)
        if not perm.get('success'):
            return perm, 403
        return f(*args, **kwargs)
    return wrapper

# ---------- Frontend ----------
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/report')
def report():
    stats = inventory_manager.get_stats()
    items = inventory_manager.get_all_items()
    staff = inventory_manager.get_all_staff()
    return render_template('report.html', stats=stats, items=items, staff=staff)

# ---------- Staff ----------
@staff_ns.route('')
class StaffList(Resource):
    def get(self):
        return safe_call(inventory_manager.get_all_staff)

    @staff_ns.expect(staff_model, validate=True)
    def post(self):
        data = request.get_json(silent=True) or {}
        res = inventory_manager.add_staff(data)
        return respond(res, ok_code=201 if res.get('success') else 400)

@staff_ns.route('/<int:user_id>')
class Staff(Resource):
    def get(self, user_id):
        staff = inventory_manager.get_staff_by_id(user_id)
        return (staff, 200) if staff else ({'error': 'Staff member not found'}, 404)

    def delete(self, user_id):
        res = inventory_manager.remove_staff(user_id)
        return respond(res)

@staff_ns.route('/auth')
class StaffAuth(Resource):
    @staff_ns.expect(auth_model, validate=True)
    def post(self):
        data = request.get_json(silent=True) or {}
        email, password = data.get('email'), data.get('password')
        if not email or not password:
            return {'success': False, 'message': 'Email and password required'}, 400
        staff = inventory_manager.authenticate_staff(email, password)
        if not staff:
            return {'success': False, 'message': 'Invalid credentials'}, 401
        return {
            'success': True,
            'message': f'Welcome {staff["name"]}!',
            'staff': staff,
            'role': staff['role']
        }, 200

@staff_ns.route('/roles')
class StaffRoles(Resource):
    def get(self):
        return {'roles': inventory_manager.get_roles()}

@staff_ns.route('/admin/add')
class AddStaff(Resource):
    @staff_ns.expect(admin_add_staff_model, validate=True)
    def post(self):
        data = request.get_json(silent=True) or {}
        admin_user_id = data.get('admin_user_id')
        if not admin_user_id or not inventory_manager.is_admin(admin_user_id):
            return {'success': False, 'message': 'Admin access required'}, 403
        payload = {k: v for k, v in data.items() if k != 'admin_user_id'}
        res = inventory_manager.add_staff(payload)
        return respond(res, ok_code=201 if res.get('success') else 400)

@staff_ns.route('/<int:user_id>/password')
class StaffPassword(Resource):
    def put(self, user_id):
        new_pw = inventory_manager._generate_secure_password()
        res = inventory_manager.update_staff(user_id, {
            'password': new_pw,
            'password_generated': True
        })
        if res.get('success'):
            res['new_password'] = new_pw
        return respond(res)

# ---------- Items ----------
@items_ns.route('')
class ItemsList(Resource):
    def get(self):
        return safe_call(inventory_manager.get_all_items)

    @items_ns.expect(item_model, validate=True)
    def post(self):
        data = request.get_json(silent=True) or {}
        res = inventory_manager.add_item(data)
        return respond(res, ok_code=201 if res.get('success') else 400)

@items_ns.route('/<string:item_id>')
class Item(Resource):
    def get(self, item_id):
        item = inventory_manager.get_item_by_id(item_id)
        return (item, 200) if item else ({'error': 'Item not found'}, 404)

    @items_ns.expect(item_model)
    def put(self, item_id):
        data = request.get_json(silent=True) or {}
        res = inventory_manager.update_item(item_id, data)
        return respond(res)

    def delete(self, item_id):
        res = inventory_manager.remove_item(item_id)
        return respond(res)

@items_ns.route('/<string:item_id>/request')
class ItemRequest(Resource):
    def post(self, item_id):
        data = request.get_json(silent=True) or {}
        res = inventory_manager.request_item(item_id, data)
        return respond(res)

@items_ns.route('/<string:item_id>/return')
class ItemReturn(Resource):
    def post(self, item_id):
        data = request.get_json(silent=True) or {}
        res = inventory_manager.return_item(item_id, data)
        return respond(res)

@items_ns.route('/<string:item_id>/availability')
class ItemAvailability(Resource):
    def put(self, item_id):
        data = request.get_json(silent=True) or {}
        status = str(data.get('status', '')).strip()
        if not status:
            return {'success': False, 'message': 'Status required'}, 400
        user_info = data.get('user_info') or {}
        res = inventory_manager.update_item_availability(item_id, status, user_info)
        return respond(res)

@items_ns.route('/available')
class AvailableItems(Resource):
    def get(self):
        return inventory_manager.get_available_items()

@items_ns.route('/reserved')
class ReservedItems(Resource):
    def get(self):
        return inventory_manager.get_reserved_items()

@items_ns.route('/<string:item_id>/schedule')
class ItemSchedule(Resource):
    @items_ns.expect(reservation_schedule_model, validate=True)
    def post(self, item_id):
        data = request.get_json(silent=True) or {}
        res = inventory_manager.schedule_item_reservation(item_id, data)
        return respond(res, ok_code=201 if res.get('success') else 400)

@items_ns.route('/<string:item_id>/reservations')
class ItemReservations(Resource):
    def get(self, item_id):
        return inventory_manager.get_item_reservations(item_id)

@items_ns.route('/<string:item_id>/reservations/<string:reservation_id>/cancel')
class CancelReservation(Resource):
    @items_ns.expect(cancel_reservation_model)
    def post(self, item_id, reservation_id):
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        admin_id = data.get('admin_user_id')
        is_admin = bool(admin_id and inventory_manager.is_admin(admin_id))
        res = inventory_manager.cancel_item_reservation(item_id, reservation_id, user_id=user_id, is_admin=is_admin)
        return respond(res)

# ---------- Utils ----------
@utils_ns.route('/stats')
class Stats(Resource):
    def get(self):
        return inventory_manager.get_stats()

@utils_ns.route('/search')
class Search(Resource):
    @utils_ns.param('q', 'Search query')
    def get(self):
        q = request.args.get('q', '')
        return inventory_manager.search_items(q)

@utils_ns.route('/departments')
class Departments(Resource):
    def get(self):
        return inventory_manager.get_departments()

@utils_ns.route('/roles')
class Roles(Resource):
    def get(self):
        return inventory_manager.get_roles()

@utils_ns.route('/locations/<string:department>')
class Locations(Resource):
    def get(self, department):
        locs = inventory_manager.get_locations_by_department(department)
        if not locs:
            return [
                "Room 101", "Room 102", "Room 201", "Room 202",
                "Room 301", "Room 302", "Storage Area"
            ]
        return locs

@utils_ns.route('/reservations/refresh')
class ReservationRefresh(Resource):
    def post(self):
        res = inventory_manager.refresh_reservation_statuses()
        return res, 200

# ---------- Static / Errors ----------
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, '../static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

if __name__ == '__main__':
    app.run(debug=True)