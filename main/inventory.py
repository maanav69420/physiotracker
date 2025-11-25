import pymongo
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from typing import Dict, List, Optional, Iterable, Any, cast
import uuid, re, random, string

def serialize_for_json(obj):
    """Recursively convert datetime objects to ISO strings."""
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_json(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

class MongoInventoryManager:
    def __init__(self, connection_string='mongodb://localhost:27017/', db_name='physiotracker_db'):
        try:
            self.client = pymongo.MongoClient(connection_string)
            self.db = self.client[db_name]
            self.client.admin.command('ismaster')
            # Ensure reservation indexes
            self.db.reservations.create_index([('item_id', pymongo.ASCENDING), ('start_datetime', pymongo.ASCENDING)])
            self.db.reservations.create_index('status')
            print("MongoDB connection successful")
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            raise

    # -------------------- Generic helpers --------------------

    def _clean_items(self, docs: Iterable[Dict]) -> List[Dict]:
        clean = []
        for d in docs:
            # normalize id
            if '_id' in d and 'id' not in d:
                d['id'] = d['_id']
            clean.append(serialize_for_json(d))
        return clean

    def _clean_staff(self, docs: Iterable[Dict]) -> List[Dict]:
        clean = []
        for d in docs:
            d = d.copy()
            d.pop('_id', None)
            d.pop('password', None)
            clean.append(serialize_for_json(d))
        return clean

    def _get_collection_name(self, location: str) -> str:
        """Map location text to collection name."""
        if not location:
            return 'general_equipment'
        m = re.search(r'(\b30[1-6]\b)', location.lower())
        if m:
            return f"b{m.group(1)}"
        return 'general_equipment'

    def _generate_secure_password(self, length: int = 12) -> str:
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    # -------------------- Item management --------------------

    def add_item(self, item_data: Dict) -> Dict:
        try:
            missing = {'name','department','quantity','location'} - set(item_data.keys())
            if missing:
                return {'success': False, 'message': f'Missing fields: {", ".join(sorted(missing))}'}
            item_id = item_data.get('id') or str(uuid.uuid4())[:8].upper()
            meta = {
                '_id': item_id,
                'id': item_id,
                'operational_status': 'available',
                'is_available': True,
                'is_reservable': True,
                'requires_attention': False,
                'equipment_type': item_data.get('equipment_type', 'non-consumable'),
                'current_stock': int(item_data.get('quantity', 1)),
                'status_updated_at': datetime.now(),
                '_imported_at': datetime.now(),
                '_last_updated': datetime.now(),
                '_active': True,
                '_version': 1
            }
            doc = {**item_data, **meta}
            col = self._get_collection_name(item_data.get('location', ''))
            self.db[col].insert_one(doc)
            self.db.all_equipment.insert_one(doc.copy())
            return {'success': True, 'message': f'Item {item_id} added successfully', 'item_id': item_id}
        except DuplicateKeyError:
            return {'success': False, 'message': f'Item ID already exists'}
        except Exception as e:
            return {'success': False, 'message': f'Error adding item: {e}'}

    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        try:
            doc = self.db.all_equipment.find_one({'_id': item_id, '_active': True})
            return self._clean_items([doc])[0] if doc else None
        except:
            return None

    def get_all_items(self) -> List[Dict]:
        try:
            return self._clean_items(self.db.all_equipment.find({'_active': True}))
        except:
            return []

    def update_item(self, item_id: str, updates: Dict) -> Dict:
        try:
            updates['_last_updated'] = datetime.now()
            res = self.db.all_equipment.update_one({'_id': item_id, '_active': True}, {'$set': updates})
            if not res.matched_count:
                return {'success': False, 'message': 'Item not found'}
            # mirror to room collection if location stored
            doc = self.get_item_by_id(item_id)
            if doc:
                col = self._get_collection_name(doc.get('location',''))
                self.db[col].update_one({'_id': item_id, '_active': True}, {'$set': updates})
            return {'success': True, 'message': f'Item {item_id} updated'}
        except Exception as e:
            return {'success': False, 'message': f'Error updating item: {e}'}

    def remove_item(self, item_id: str) -> Dict:
        try:
            doc = self.get_item_by_id(item_id)
            if not doc:
                return {'success': False, 'message': 'Item not found'}
            room_col = self._get_collection_name(doc.get('location',''))
            self.db[room_col].delete_one({'_id': item_id})
            self.db.all_equipment.delete_one({'_id': item_id})
            return {'success': True, 'message': f'Item {item_id} removed'}
        except Exception as e:
            return {'success': False, 'message': f'Error removing item: {e}'}

    # -------------------- Item search / filter --------------------

    def search_items(self, query: str) -> List[Dict]:
        try:
            f = {
                '_active': True,
                '$or': [
                    {'equipment_name': {'$regex': query, '$options': 'i'}},
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'_id': {'$regex': query, '$options': 'i'}},
                    {'lab_name': {'$regex': query, '$options': 'i'}},
                    {'room_no': {'$regex': query, '$options': 'i'}}
                ]
            }
            return self._clean_items(self.db.all_equipment.find(f))
        except:
            return []

    def filter_items_by_department(self, department: str) -> List[Dict]:
        if department == 'all':
            return self.get_all_items()
        try:
            f = {'_active': True, 'lab_name': {'$regex': department, '$options': 'i'}}
            return self._clean_items(self.db.all_equipment.find(f))
        except:
            return []

    def filter_items_by_status(self, status: str) -> List[Dict]:
        try:
            return self._clean_items(self.db.all_equipment.find({'_active': True,'operational_status': status}))
        except:
            return []

    def get_available_items(self) -> List[Dict]:
        return self.filter_items_by_status('available')

    def get_reserved_items(self) -> List[Dict]:
        """Return items marked as reserved or scheduled in operational_status."""
        try:
            return self._clean_items(self.db.all_equipment.find({
                '_active': True,
                'operational_status': {'$in': ['reserved', 'scheduled']}
            }))
        except Exception as e:
            print(f"Error fetching reserved items: {e}")
            return []

    # -------------------- Reservation / status --------------------
    def _parse_iso(self, value: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    def _overlaps(self, a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
        return a_start < b_end and a_end > b_start

    def get_item_reservations(self, item_id: str, include_cancelled: bool = False) -> List[Dict[str, Any]]:
        """Return reservations for an item."""
        try:
            q: Dict[str, Any] = {'item_id': item_id}
            if not include_cancelled:
                q['status'] = {'$in': ['scheduled', 'active']}
            docs = list(self.db.reservations.find(q).sort('start_datetime', 1))
            return [cast(Dict[str, Any], serialize_for_json(d)) for d in docs]
        except:
            return []

    def schedule_item_reservation(self, item_id: str, data: Dict) -> Dict:
        """
        Schedule a reservation for a future (or current) time window.
        Expected data: user_id, user_name, start_datetime (ISO), end_datetime (ISO), notes(optional)
        """
        item = self.get_item_by_id(item_id)
        if not item:
            return {'success': False, 'message': 'Item not found'}

        for f in ['user_id', 'user_name', 'start_datetime', 'end_datetime']:
            if f not in data:
                return {'success': False, 'message': f'Missing field {f}'}

        start_dt = self._parse_iso(data['start_datetime'])
        end_dt = self._parse_iso(data['end_datetime'])
        if not start_dt or not end_dt:
            return {'success': False, 'message': 'Invalid datetime format (use ISO 8601)'}
        if end_dt <= start_dt:
            return {'success': False, 'message': 'end_datetime must be after start_datetime'}

        now = datetime.now()
        # Fetch existing scheduled/active reservations for overlap check
        existing = list(self.db.reservations.find({
            'item_id': item_id,
            'status': {'$in': ['scheduled', 'active']}
        }))
        for r in existing:
            if self._overlaps(start_dt, end_dt, r['start_datetime'], r['end_datetime']):
                return {'success': False, 'message': 'Time window overlaps existing reservation'}

        # Determine reservation status
        res_status = 'active' if start_dt <= now < end_dt else 'scheduled'
        reservation_id = str(uuid.uuid4())[:8]

        reservation_doc = {
            '_id': reservation_id,
            'reservation_id': reservation_id,
            'item_id': item_id,
            'user_id': data['user_id'],
            'user_name': data['user_name'],
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'notes': data.get('notes', ''),
            'created_at': now,
            'status': res_status
        }
        self.db.reservations.insert_one(reservation_doc)

        # Update item status if currently active reservation
        if res_status == 'active':
            self.update_item(item_id, {
                'operational_status': 'reserved',
                'is_available': False,
                'is_reservable': False,
                'reserved_by': data['user_id'],
                'reserved_by_name': data['user_name'],
                'reservation_date': now
            })
        else:
            # Mark item as having a future reservation (scheduled)
            self.update_item(item_id, {
                'operational_status': 'scheduled',
                'is_reservable': False
            })

        return {
            'success': True,
            'message': f'Reservation {reservation_id} {"active" if res_status=="active" else "scheduled"}',
            'reservation': serialize_for_json(reservation_doc)
        }

    def cancel_item_reservation(self, item_id: str, reservation_id: str, user_id: Optional[int] = None, is_admin: bool = False) -> Dict:
        """Cancel a reservation if requester owns it or is admin."""
        res_doc = self.db.reservations.find_one({'_id': reservation_id, 'item_id': item_id})
        if not res_doc:
            return {'success': False, 'message': 'Reservation not found'}

        if not is_admin and user_id is not None and res_doc.get('user_id') != user_id:
            return {'success': False, 'message': 'Not authorized to cancel this reservation'}

        if res_doc.get('status') in ['cancelled', 'completed']:
            return {'success': False, 'message': 'Reservation already closed'}

        self.db.reservations.update_one({'_id': reservation_id}, {'$set': {'status': 'cancelled', 'cancelled_at': datetime.now()}})

        # Recompute item status
        now = datetime.now()
        active_left = self.db.reservations.count_documents({
            'item_id': item_id,
            'status': 'active',
            'start_datetime': {'$lte': now},
            'end_datetime': {'$gt': now}
        })
        future_left = self.db.reservations.count_documents({
            'item_id': item_id,
            'status': 'scheduled',
            'start_datetime': {'$gt': now}
        })

        if active_left:
            self.update_item(item_id, {'operational_status': 'reserved', 'is_available': False})
        elif future_left:
            self.update_item(item_id, {'operational_status': 'scheduled', 'is_available': True})
        else:
            self.update_item(item_id, {
                'operational_status': 'available',
                'is_available': True,
                'is_reservable': True,
                'reserved_by': None,
                'reserved_by_name': None
            })

        return {'success': True, 'message': f'Reservation {reservation_id} cancelled'}

    def refresh_reservation_statuses(self) -> Dict:
        """Promote scheduled -> active and active -> completed based on current time."""
        now = datetime.now()
        changed_active = 0
        changed_completed = 0

        # Promote scheduled
        scheduled_cursor = self.db.reservations.find({
            'status': 'scheduled',
            'start_datetime': {'$lte': now},
            'end_datetime': {'$gt': now}
        })
        for r in scheduled_cursor:
            self.db.reservations.update_one({'_id': r['_id']}, {'$set': {'status': 'active', 'activated_at': now}})
            # Set item to reserved if not already
            self.update_item(r['item_id'], {
                'operational_status': 'reserved',
                'is_available': False,
                'is_reservable': False,
                'reserved_by': r.get('user_id'),
                'reserved_by_name': r.get('user_name'),
                'reservation_date': now
            })
            changed_active += 1

        # Complete expired active
        active_cursor = self.db.reservations.find({
            'status': 'active',
            'end_datetime': {'$lte': now}
        })
        for r in active_cursor:
            self.db.reservations.update_one({'_id': r['_id']}, {'$set': {'status': 'completed', 'completed_at': now}})
            # Recompute item status (may have other future reservations)
            future_left = self.db.reservations.count_documents({
                'item_id': r['item_id'],
                'status': 'scheduled',
                'start_datetime': {'$gt': now}
            })
            active_left = self.db.reservations.count_documents({
                'item_id': r['item_id'],
                'status': 'active',
                'start_datetime': {'$lte': now},
                'end_datetime': {'$gt': now}
            })
            if active_left:
                self.update_item(r['item_id'], {'operational_status': 'reserved', 'is_available': False})
            elif future_left:
                self.update_item(r['item_id'], {'operational_status': 'scheduled', 'is_available': True})
            else:
                self.update_item(r['item_id'], {
                    'operational_status': 'available',
                    'is_available': True,
                    'is_reservable': True,
                    'reserved_by': None,
                    'reserved_by_name': None
                })
            changed_completed += 1

        return {
            'success': True,
            'activated': changed_active,
            'completed': changed_completed,
            'timestamp': now.isoformat()
        }

    # -------------------- Stats --------------------

    def get_stats(self) -> Dict:
        try:
            pipeline = [
                {'$match': {'_active': True}},
                {'$group': {
                    '_id': None,
                    'total_items': {'$sum': 1},
                    'available_items': {'$sum': {'$cond':[{'$eq':['$operational_status','available']},1,0]}},
                    'reserved_items': {'$sum': {'$cond':[{'$eq':['$operational_status','reserved']},1,0]}},
                    'maintenance_items': {'$sum': {'$cond':[{'$eq':['$operational_status','maintenance']},1,0]}},
                }}
            ]
            result = list(self.db.all_equipment.aggregate(pipeline))
            if not result:
                return {'total_items':0,'available_items':0,'reserved_items':0,'maintenance_items':0,
                        'availability_rate':0,'utilization_rate':0}
            stats = result[0]; stats.pop('_id',None)
            total = stats.get('total_items',0)
            stats['availability_rate'] = round((stats.get('available_items',0)/total)*100,1) if total else 0
            stats['utilization_rate'] = round((stats.get('reserved_items',0)/total)*100,1) if total else 0
            return stats
        except:
            return {}

    def get_departments(self) -> List[str]:
        try:
            return sorted([d for d in self.db.all_equipment.distinct('lab_name', {'_active': True}) if d])
        except:
            return []

    def get_locations_by_department(self, department: str) -> List[str]:
        try:
            rooms = self.db.all_equipment.distinct('room_no', {
                '_active': True,
                'lab_name': {'$regex': department, '$options': 'i'}
            })
            return sorted([f"Room {r}" for r in rooms if r])
        except:
            return []

    # -------------------- Staff management --------------------

    def get_roles(self) -> List[str]:
        return ['admin','staff']

    def add_staff(self, staff_data: Dict) -> Dict:
        try:
            missing = {'name','email','department','role'} - set(staff_data.keys())
            if missing:
                return {'success': False,'message': f'Missing fields: {", ".join(sorted(missing))}'}
            if staff_data['role'].lower() not in {'admin','staff'}:
                return {'success': False,'message':'Role must be admin or staff'}
            if self.db.staff.find_one({'email': staff_data['email']}):
                return {'success': False,'message':'Email already exists'}
            highest = self.db.staff.find_one({}, sort=[('user_id', -1)])
            staff_data['user_id'] = (highest['user_id'] + 1) if highest else 1001
            if not staff_data.get('password'):
                staff_data['password'] = self._generate_secure_password()
                staff_data['password_generated'] = True
            staff_doc = {
                **staff_data,
                '_id': staff_data['user_id'],
                'role': staff_data['role'].lower(),
                'created_at': datetime.now(),
                'last_updated': datetime.now(),
                'active': True
            }
            self.db.staff.insert_one(staff_doc)
            resp = {'success': True,'message': f'{staff_doc["role"].title()} {staff_doc["name"]} added','user_id': staff_doc['user_id']}
            if staff_doc.get('password_generated'):
                resp['generated_password'] = staff_doc['password']
            return resp
        except Exception as e:
            return {'success': False,'message': f'Error adding staff: {e}'}

    def authenticate_staff(self, email: str, password: str) -> Optional[Dict]:
        doc = self.db.staff.find_one({'email': email,'password': password,'active': True})
        if not doc:
            return None
        self.db.staff.update_one({'user_id': doc['user_id']},{'$set': {'last_login': datetime.now()}})
        return self._clean_staff([doc])[0]

    def get_all_staff(self) -> List[Dict]:
        try:
            return self._clean_staff(self.db.staff.find({'active': True}))
        except:
            return []

    def get_staff_by_id(self, user_id: int) -> Optional[Dict]:
        doc = self.db.staff.find_one({'user_id': user_id,'active': True})
        return self._clean_staff([doc])[0] if doc else None

    def update_staff(self, user_id: int, updates: Dict) -> Dict:
        updates['last_updated'] = datetime.now()
        res = self.db.staff.update_one({'user_id': user_id,'active': True},{'$set': updates})
        if not res.matched_count:
            return {'success': False,'message':'Staff not found'}
        return {'success': True,'message': f'Staff {user_id} updated'}

    def remove_staff(self, user_id: int) -> Dict:
        res = self.db.staff.update_one({'user_id': user_id},{'$set': {'active': False,'deactivated_at': datetime.now()}})
        if not res.matched_count:
            return {'success': False,'message':'Staff not found'}
        return {'success': True,'message': f'Staff {user_id} removed'}

    def is_admin(self, user_id: int) -> bool:
        doc = self.db.staff.find_one({'user_id': user_id,'active': True})
        return bool(doc and doc.get('role') == 'admin')

    def check_admin_permission(self, user_id: int) -> Dict:
        return {'success': True,'message':'Admin access granted'} if self.is_admin(user_id) else {'success': False,'message':'Admin access required'}

    def update_item_availability(self, item_id: str, status: str, user_info: Optional[Dict] = None) -> Dict:
        valid = {'available','reserved','in_use','maintenance','cleaning','out_of_order','scheduled'}
        if status not in valid:
            return {'success': False, 'message': f'Invalid status. Must be one of {", ".join(valid)}'}
        try:
            now = datetime.now()
            updates = {
                'operational_status': status,
                'is_available': status == 'available',
                'is_reservable': status in {'available', 'reserved'},
                'status_updated_at': now
            }
            self.db.all_equipment.update_one({'_id': item_id}, {'$set': updates})
            # mirror to specific room collection if location known
            item = self.get_item_by_id(item_id)
            if item:
                col = self._get_collection_name(item.get('location',''))
                self.db[col].update_one({'_id': item_id}, {'$set': updates})
            return {'success': True, 'message': f'Item {item_id} status updated to {status}'}
        except Exception as e:
            return {'success': False, 'message': f'Error updating item status: {e}'}