import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class JSONDatabase:
    def __init__(self, data_file: str = "data/database.json"):
        self.data_file = data_file
        self.ensure_data_file()
    
    def ensure_data_file(self):
        """Create data file if it doesn't exist"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            # Create empty structure if file doesn't exist
            empty_db = {
                "schema": {"departments": [], "roles": [], "locations": {}},
                "users": [], "items": [], "reservations": [],
                "maintenance_logs": [], "usage_logs": [],
                "settings": {}, "metadata": {}
            }
            self.save_data(empty_db)
    
    def load_data(self) -> Dict:
        """Load all data from JSON file"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading data: {e}")
            return {}
    
    def save_data(self, data: Dict) -> bool:
        """Save all data to JSON file"""
        try:
            # Update metadata
            if 'metadata' not in data:
                data['metadata'] = {}
            
            data['metadata']['last_updated'] = datetime.now().isoformat()
            data['metadata']['total_items'] = len(data.get('items', []))
            data['metadata']['total_users'] = len(data.get('users', []))
            
            with open(self.data_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False
    
    # ============ STAFF MANAGEMENT FUNCTIONS ============
    
    def add_staff(self, staff_data: Dict) -> Dict:
        """Add new staff member"""
        try:
            data = self.load_data()
            
            # Validate required fields
            required_fields = ['name', 'email', 'department', 'role']
            for field in required_fields:
                if field not in staff_data or not staff_data[field]:
                    return {'success': False, 'message': f'Missing required field: {field}'}
            
            # Check if email already exists
            existing_users = data.get('users', [])
            if any(user['email'] == staff_data['email'] for user in existing_users):
                return {'success': False, 'message': 'Email already exists'}
            
            # Validate department and role
            departments = data.get('schema', {}).get('departments', [])
            roles = data.get('schema', {}).get('roles', [])
            
            if staff_data['department'] not in departments:
                return {'success': False, 'message': f'Invalid department: {staff_data["department"]}'}
            
            if staff_data['role'] not in roles:
                return {'success': False, 'message': f'Invalid role: {staff_data["role"]}'}
            
            # Generate new user ID
            existing_ids = [user.get('id', 0) for user in existing_users]
            new_id = max(existing_ids, default=0) + 1
            
            # Create new staff member
            new_staff = {
                'id': new_id,
                'name': staff_data['name'],
                'email': staff_data['email'],
                'password': staff_data.get('password', 'temp123'),  # Default password
                'department': staff_data['department'],
                'role': staff_data['role'],
                'phone': staff_data.get('phone', ''),
                'created_date': datetime.now().strftime('%Y-%m-%d'),
                'last_login': None,
                'permissions': self._get_default_permissions(staff_data['role'])
            }
            
            # Add to users list
            data['users'].append(new_staff)
            
            if self.save_data(data):
                return {'success': True, 'message': 'Staff member added successfully', 'user_id': new_id}
            else:
                return {'success': False, 'message': 'Failed to save data'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error adding staff: {str(e)}'}
    
    def remove_staff(self, user_id: int) -> Dict:
        """Remove staff member by ID"""
        try:
            data = self.load_data()
            users = data.get('users', [])
            
            # Find user to remove
            user_to_remove = None
            user_index = None
            
            for i, user in enumerate(users):
                if user.get('id') == user_id:
                    user_to_remove = user
                    user_index = i
                    break
            
            if not user_to_remove:
                return {'success': False, 'message': f'Staff member with ID {user_id} not found'}
            
            # Check if user has active reservations
            reservations = data.get('reservations', [])
            active_reservations = [r for r in reservations if r.get('user_id') == user_id and r.get('status') == 'active']
            
            if active_reservations:
                return {'success': False, 'message': f'Cannot remove staff member. {len(active_reservations)} active reservations found'}
            
            # Remove user
            removed_user_name = user_to_remove['name']
            del users[user_index]
            
            if self.save_data(data):
                return {'success': True, 'message': f'Staff member {removed_user_name} removed successfully'}
            else:
                return {'success': False, 'message': 'Failed to save data'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error removing staff: {str(e)}'}
    
    def get_all_staff(self) -> List[Dict]:
        """Get all staff members"""
        data = self.load_data()
        return data.get('users', [])
    
    def get_staff_by_id(self, user_id: int) -> Optional[Dict]:
        """Get staff member by ID"""
        users = self.get_all_staff()
        return next((user for user in users if user['id'] == user_id), None)
    
    # ============ ITEM MANAGEMENT FUNCTIONS ============
    
    def add_item(self, item_data: Dict) -> Dict:
        """Add new inventory item"""
        try:
            data = self.load_data()
            
            # Validate required fields
            required_fields = ['id', 'name', 'department', 'quantity', 'location']
            for field in required_fields:
                if field not in item_data or not item_data[field]:
                    return {'success': False, 'message': f'Missing required field: {field}'}
            
            # Check if item ID already exists
            existing_items = data.get('items', [])
            if any(item['id'] == item_data['id'] for item in existing_items):
                return {'success': False, 'message': f'Item ID {item_data["id"]} already exists'}
            
            # Validate department
            departments = data.get('schema', {}).get('departments', [])
            if item_data['department'] not in departments:
                return {'success': False, 'message': f'Invalid department: {item_data["department"]}'}
            
            # Validate location for department
            locations = data.get('schema', {}).get('locations', {})
            dept_locations = locations.get(item_data['department'], [])
            if item_data['location'] not in dept_locations:
                return {'success': False, 'message': f'Invalid location for department: {item_data["location"]}'}
            
            # Create new item
            new_item = {
                'id': item_data['id'],
                'name': item_data['name'],
                'description': item_data.get('description', ''),
                'department': item_data['department'],
                'quantity': int(item_data['quantity']),
                'min_stock_level': int(item_data.get('min_stock_level', 1)),
                'location': item_data['location'],
                'status': item_data.get('status', 'available'),
                'supplier': item_data.get('supplier', ''),
                'last_used': datetime.now().strftime('%Y-%m-%d'),
                'assigned_to': item_data.get('assigned_to', 'head'),
                'usage_count': 0
            }
            
            # Add to items list
            data['items'].append(new_item)
            
            if self.save_data(data):
                return {'success': True, 'message': f'Item {item_data["id"]} added successfully'}
            else:
                return {'success': False, 'message': 'Failed to save data'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error adding item: {str(e)}'}
    
    def remove_item(self, item_id: str) -> Dict:
        """Remove inventory item by ID"""
        try:
            data = self.load_data()
            items = data.get('items', [])
            
            # Find item to remove
            item_to_remove = None
            item_index = None
            
            for i, item in enumerate(items):
                if item.get('id') == item_id:
                    item_to_remove = item
                    item_index = i
                    break
            
            if not item_to_remove:
                return {'success': False, 'message': f'Item {item_id} not found'}
            
            # Check if item has active reservations
            reservations = data.get('reservations', [])
            active_reservations = [r for r in reservations if r.get('item_id') == item_id and r.get('status') == 'active']
            
            if active_reservations:
                return {'success': False, 'message': f'Cannot remove item. {len(active_reservations)} active reservations found'}
            
            # Check if item is in maintenance
            if item_to_remove.get('status') == 'maintenance':
                return {'success': False, 'message': 'Cannot remove item currently in maintenance'}
            
            # Remove item
            removed_item_name = item_to_remove['name']
            del items[item_index]
            
            if self.save_data(data):
                return {'success': True, 'message': f'Item {removed_item_name} ({item_id}) removed successfully'}
            else:
                return {'success': False, 'message': 'Failed to save data'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error removing item: {str(e)}'}
    
    def get_all_items(self) -> List[Dict]:
        """Get all inventory items"""
        data = self.load_data()
        return data.get('items', [])
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """Get item by ID"""
        items = self.get_all_items()
        return next((item for item in items if item['id'] == item_id), None)
    
    def update_item(self, item_id: str, updates: Dict) -> Dict:
        """Update existing item"""
        try:
            data = self.load_data()
            items = data.get('items', [])
            
            for i, item in enumerate(items):
                if item['id'] == item_id:
                    # Update item fields
                    items[i].update(updates)
                    
                    if self.save_data(data):
                        return {'success': True, 'message': f'Item {item_id} updated successfully'}
                    else:
                        return {'success': False, 'message': 'Failed to save data'}
            
            return {'success': False, 'message': f'Item {item_id} not found'}
            
        except Exception as e:
            return {'success': False, 'message': f'Error updating item: {str(e)}'}
    
    # ============ HELPER FUNCTIONS ============
    
    def _get_default_permissions(self, role: str) -> List[str]:
        """Get default permissions based on role"""
        permission_map = {
            'head': ['all'],
            'lab_assistant': ['read', 'update', 'reserve'],
            'co_lab_assistant': ['read', 'reserve']
        }
        return permission_map.get(role, ['read'])
    
    def get_departments(self) -> List[str]:
        """Get all departments"""
        data = self.load_data()
        return data.get('schema', {}).get('departments', [])
    
    def get_roles(self) -> List[str]:
        """Get all roles"""
        data = self.load_data()
        return data.get('schema', {}).get('roles', [])
    
    def get_locations_by_department(self, department: str) -> List[str]:
        """Get locations for a specific department"""
        data = self.load_data()
        locations = data.get('schema', {}).get('locations', {})
        return locations.get(department, [])
    
    # ============ STATISTICS FUNCTIONS ============
    
    def get_inventory_stats(self) -> Dict:
        """Get inventory statistics"""
        items = self.get_all_items()
        users = self.get_all_staff()
        
        stats = {
            'total_items': len(items),
            'total_staff': len(users),
            'available': len([i for i in items if i['status'] == 'available']),
            'reserved': len([i for i in items if i['status'] == 'reserved']),
            'maintenance': len([i for i in items if i['status'] == 'maintenance']),
            'low_stock': len([i for i in items if i['quantity'] <= i.get('min_stock_level', 0)]),
            'by_department': {}
        }
        
        # Department breakdown
        for dept in self.get_departments():
            dept_items = [i for i in items if i['department'] == dept]
            stats['by_department'][dept] = len(dept_items)
        
        return stats