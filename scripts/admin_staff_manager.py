import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main.inventory import MongoInventoryManager
from datetime import datetime
import getpass

class AdminStaffManager:
    def __init__(self):
        """Initialize admin staff management"""
        try:
            self.inventory_manager = MongoInventoryManager()
            print("Connected to PhysioTracker database")
        except Exception as e:
            print(f"Database connection failed: {e}")
            exit(1)
    
    def show_menu(self):
        """Display admin menu"""
        print("\n" + "="*50)
        print("PhysioTracker Admin - Staff Management")
        print("="*50)
        print("1. View All Staff")
        print("2. Add Admin User") 
        print("3. Add Staff User")
        print("4. Remove Staff Member")
        print("5. Reset Staff Password")
        print("6. View Staff Statistics")
        print("7. Exit")
        print("-"*50)
    
    def view_all_staff(self):
        """Display all staff members"""
        print("\nAll Staff Members:")
        print("-"*70)
        
        staff_list = self.inventory_manager.get_all_staff()
        
        if not staff_list:
            print("No staff members found.")
            return
        
        print(f"{'ID':<6} {'Name':<20} {'Email':<25} {'Role':<8} {'Department':<10}")
        print("-"*70)
        
        for staff in staff_list:
            print(f"{staff.get('user_id', 'N/A'):<6} "
                  f"{staff.get('name', 'N/A'):<20} "
                  f"{staff.get('email', 'N/A'):<25} "
                  f"{staff.get('role', 'N/A').upper():<8} "
                  f"{staff.get('department', 'N/A'):<10}")
        
        print(f"\nTotal staff members: {len(staff_list)}")
    
    def add_admin_user(self):
        """Add admin user"""
        print("\nAdd Admin User:")
        print("-"*20)
        
        try:
            name = input("Admin Name: ").strip()
            email = input("Admin Email: ").strip()
            department = input("Department (default: Administration): ").strip()
            if not department:
                department = "Administration"
            
            password = getpass.getpass("Admin Password: ")
            
            if not all([name, email, password]):
                print("Error: Name, email, and password are required")
                return
            
            admin_data = {
                'name': name,
                'email': email,
                'password': password,
                'role': 'admin',
                'department': department,
                'phone': input("Phone (optional): ").strip() or None
            }
            
            result = self.inventory_manager.add_staff(admin_data)
            
            if result['success']:
                print(f"Success: {result['message']}")
                print(f"User ID: {result['user_id']}")
            else:
                print(f"Error: {result['message']}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"Error: {e}")
    
    def add_staff_user(self):
        """Add staff user"""
        print("\nAdd Staff User:")
        print("-"*20)
        
        try:
            name = input("Staff Name: ").strip()
            email = input("Staff Email: ").strip()
            
            print("\nAvailable departments:")
            departments = self.inventory_manager.get_departments()
            for i, dept in enumerate(departments, 1):
                print(f"{i}. {dept}")
            
            dept_choice = input("Select department (number or type manually): ").strip()
            try:
                department = departments[int(dept_choice) - 1]
            except:
                if dept_choice.isdigit():
                    department = input("Enter department manually: ").strip()
                else:
                    department = dept_choice
            
            phone = input("Phone (optional): ").strip()
            
            # Ask if admin wants to set password or generate one
            set_password = input("Set custom password? (y/n): ").lower() == 'y'
            password = None
            if set_password:
                password = getpass.getpass("Enter password: ")
            
            staff_data = {
                'name': name,
                'email': email,
                'department': department,
                'role': 'staff',
                'phone': phone if phone else None
            }
            
            if password:
                staff_data['password'] = password
            
            result = self.inventory_manager.add_staff(staff_data)
            
            if result['success']:
                print(f"\nSuccess: {result['message']}")
                if 'generated_password' in result:
                    print(f"Generated Password: {result['generated_password']}")
                    print("Make sure to share this password securely with the staff member.")
            else:
                print(f"Error: {result['message']}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"Error: {e}")
    
    def remove_staff_member(self):
        """Remove staff member"""
        print("\nRemove Staff Member:")
        print("-"*25)
        
        try:
            self.view_all_staff()
            
            user_id = input("\nEnter User ID to remove: ").strip()
            if not user_id:
                print("Error: User ID is required")
                return
            
            try:
                user_id = int(user_id)
            except:
                print("Error: User ID must be a number")
                return
            
            staff = self.inventory_manager.get_staff_by_id(user_id)
            if not staff:
                print(f"Error: Staff member {user_id} not found")
                return
            
            print(f"\nStaff to remove:")
            print(f"Name: {staff['name']}")
            print(f"Email: {staff['email']}")
            print(f"Role: {staff['role'].upper()}")
            
            confirm = input("\nConfirm removal (type 'YES' to confirm): ")
            if confirm != 'YES':
                print("Removal cancelled.")
                return
            
            result = self.inventory_manager.remove_staff(user_id)
            
            if result['success']:
                print(f"Success: {result['message']}")
            else:
                print(f"Error: {result['message']}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"Error: {e}")
    
    def reset_staff_password(self):
        """Reset staff member password"""
        print("\nReset Staff Password:")
        print("-"*25)
        
        try:
            self.view_all_staff()
            
            user_id = input("\nEnter User ID: ").strip()
            if not user_id:
                print("Error: User ID is required")
                return
            
            try:
                user_id = int(user_id)
            except:
                print("Error: User ID must be a number")
                return
            
            staff = self.inventory_manager.get_staff_by_id(user_id)
            if not staff:
                print(f"Error: Staff member {user_id} not found")
                return
            
            print(f"\nResetting password for: {staff['name']} ({staff['role'].upper()})")
            
            # Generate new password
            new_password = self.inventory_manager._generate_secure_password()
            
            result = self.inventory_manager.update_staff(user_id, {
                'password': new_password,
                'password_generated': True
            })
            
            if result['success']:
                print(f"Success: Password reset successfully")
                print(f"New Password: {new_password}")
                print("Make sure to share this password securely with the staff member.")
            else:
                print(f"Error: {result['message']}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"Error: {e}")
    
    def view_staff_stats(self):
        """Show staff statistics"""
        print("\nStaff Statistics:")
        print("-"*25)
        
        try:
            staff_list = self.inventory_manager.get_all_staff()
            
            if not staff_list:
                print("No staff members found.")
                return
            
            # Count by role
            admin_count = sum(1 for s in staff_list if s.get('role') == 'admin')
            staff_count = sum(1 for s in staff_list if s.get('role') == 'staff')
            
            # Count by department
            dept_counts = {}
            for staff in staff_list:
                dept = staff.get('department', 'unknown')
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            print(f"Total Staff: {len(staff_list)}")
            print(f"\nBy Role:")
            print(f"  Admin: {admin_count}")
            print(f"  Staff: {staff_count}")
            
            print(f"\nBy Department:")
            for dept, count in dept_counts.items():
                print(f"  {dept}: {count}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    def run(self):
        """Main admin interface loop"""
        print("Welcome to PhysioTracker Admin Interface")
        
        while True:
            try:
                self.show_menu()
                choice = input("Select option (1-7): ").strip()
                
                if choice == '1':
                    self.view_all_staff()
                elif choice == '2':
                    self.add_admin_user()
                elif choice == '3':
                    self.add_staff_user()
                elif choice == '4':
                    self.remove_staff_member()
                elif choice == '5':
                    self.reset_staff_password()
                elif choice == '6':
                    self.view_staff_stats()
                elif choice == '7':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please select 1-7.")
                    
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    admin_manager = AdminStaffManager()
    admin_manager.run()