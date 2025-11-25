import pandas as pd
import pymongo
from pymongo.errors import ServerSelectionTimeoutError
from pathlib import Path
from datetime import datetime, timedelta
import sys

def connect_to_mongodb():
    """Connect to MongoDB and return database object"""
    try:
        print("Connecting to MongoDB...")
        client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ismaster')
        print("Connected to MongoDB successfully!")
        
        # Get database
        db = client['physiotracker_db']
        print(f"Using database: physiotracker_db")
        
        return client, db
    except ServerSelectionTimeoutError:
        print("MongoDB connection failed!")
        print("Make sure MongoDB is running and accessible at localhost:27017")
        return None, None
        
    except Exception as e:
        print(f"Connection error: {e}")
        return None, None
        return None, None

def determine_default_status(equipment_type):
    """Determine default operational status based on equipment type"""
    equipment_type = str(equipment_type).lower()
    
    if equipment_type == 'consumable':
        # Consumables might need stock management
        return 'available'
    elif equipment_type == 'non-consumable':
        # Non-consumables are typically always available unless broken
        return 'available'
    else:
        return 'available'

def add_equipment_metadata(record):
    """Add equipment tracking metadata"""
    now = datetime.now()
    equipment_type = record.get('equipment_type', 'unknown')
    
    # Add operational status tracking
    record['operational_status'] = record.get('operational_status', 'available')
    record['status_updated_at'] = now
    record['status_history'] = [{
        'status': record['operational_status'],
        'timestamp': now,
        'reason': 'initial_import',
        'updated_by': 'system'
    }]
    
    # Add availability fields based on operational status
    record['is_available'] = record['operational_status'] == 'available'
    record['is_reservable'] = record['operational_status'] in ['available', 'cleaning']
    record['requires_attention'] = record['operational_status'] in ['maintenance', 'out_of_order']
    
    # Add equipment-type specific fields
    if equipment_type == 'consumable':
        record['is_consumable'] = True
        record['tracks_quantity'] = True
        record['current_stock'] = record.get('quantity', 1)  # Default to 1 if no quantity specified
    else:
        record['is_consumable'] = False
        record['tracks_quantity'] = False
        record['current_stock'] = 1  # Non-consumables are individual items
    
    # Add estimated availability
    if record['operational_status'] == 'maintenance':
        record['estimated_available_date'] = now + timedelta(days=5)
    elif record['operational_status'] == 'cleaning':
        record['estimated_available_date'] = now + timedelta(hours=2)
    else:
        record['estimated_available_date'] = now
    
    return record

def process_csv_file(csv_path, collection_name):
    """Process CSV file with correct equipment type handling"""
    try:
        print(f"  Reading {csv_path.name}...")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        if df.empty:
            print(f"  Warning: {csv_path.name} is empty")
            return []
        
        print(f"  Processing {len(df)} rows...")
        print(f"  Columns: {list(df.columns)}")
        
        # Convert to dictionary records
        records = df.to_dict('records')
        processed_records = []
        
        for i, record in enumerate(records):
            # Clean up the record
            clean_record = {}
            
            for key, value in record.items():
                # Clean column names
                clean_key = str(key).lower().strip().replace(' ', '_').replace('-', '_')
                
                # Clean values
                if pd.isna(value):
                    clean_record[clean_key] = ""
                else:
                    clean_record[clean_key] = str(value).strip()
            
            # Handle the status column as equipment type/class
            if 'status' in clean_record:
                # Rename status to equipment_type for clarity
                clean_record['equipment_type'] = clean_record['status'].lower()
                # Remove the old status column to avoid confusion
                del clean_record['status']
            else:
                clean_record['equipment_type'] = 'unknown'
            
            # Set default operational status
            clean_record['operational_status'] = determine_default_status(clean_record['equipment_type'])
            
            # Add MongoDB metadata
            clean_record['_id'] = f"{collection_name}_{i+1:04d}"
            clean_record['_imported_at'] = datetime.now()
            clean_record['_source_file'] = csv_path.name
            clean_record['_collection'] = collection_name
            clean_record['_room_code'] = collection_name.upper()
            
            # Add equipment metadata
            clean_record = add_equipment_metadata(clean_record)
            
            # Add tracking fields
            clean_record['_last_updated'] = datetime.now()
            clean_record['_active'] = True
            clean_record['_version'] = 1
            
            processed_records.append(clean_record)
        
        # Show processing results
        type_counts = {}
        status_counts = {}
        
        for record in processed_records:
            eq_type = record.get('equipment_type', 'unknown')
            op_status = record.get('operational_status', 'unknown')
            
            type_counts[eq_type] = type_counts.get(eq_type, 0) + 1
            status_counts[op_status] = status_counts.get(op_status, 0) + 1
        
        print(f"  Equipment types: {type_counts}")
        print(f"  Operational status: {status_counts}")
        print(f"  Processed {len(processed_records)} records successfully")
        
        return processed_records
        
    except Exception as e:
        print(f"  Error processing {csv_path.name}: {e}")
        return []

def create_indexes(db, collection_name):
    """Create indexes for efficient querying"""
    try:
        collection = db[collection_name]
        
        # Equipment classification indexes
        collection.create_index([("equipment_type", 1)])
        collection.create_index([("is_consumable", 1)])
        
        # Operational status indexes
        collection.create_index([("operational_status", 1)])
        collection.create_index([("is_available", 1)])
        collection.create_index([("is_reservable", 1)])
        collection.create_index([("requires_attention", 1)])
        
        # Equipment identification
        collection.create_index([("equipment_name", 1)])
        collection.create_index([("room_no", 1)])
        collection.create_index([("_room_code", 1)])
        
        # Compound indexes for common queries
        collection.create_index([("equipment_type", 1), ("operational_status", 1)])
        collection.create_index([("operational_status", 1), ("_room_code", 1)])
        collection.create_index([("is_available", 1), ("equipment_name", 1)])
        collection.create_index([("equipment_name", 1), ("operational_status", 1)])
        collection.create_index([("equipment_type", 1), ("_room_code", 1)])
        
        # Time-based indexes
        collection.create_index([("status_updated_at", -1)])
        collection.create_index([("estimated_available_date", 1)])
        collection.create_index([("_imported_at", -1)])
        
        # Stock management indexes (for consumables)
        collection.create_index([("is_consumable", 1), ("current_stock", 1)])
        
        print(f"  Created indexes for {collection_name}")
        
    except Exception as e:
        print(f"  Warning: Index creation failed for {collection_name}: {e}")

def create_master_collection(db):
    """Create master collection combining all equipment"""
    try:
        print("Creating master collection...")
        
        all_equipment = []
        room_collections = [name for name in db.list_collection_names() 
                          if name.startswith('b30') and len(name) == 4]
        
        for collection_name in room_collections:
            items = list(db[collection_name].find({}))
            all_equipment.extend(items)
        
        if all_equipment:
            # Drop and recreate master collection
            db.all_equipment.drop()
            db.all_equipment.insert_many(all_equipment)
            
            # Create indexes for master collection
            create_indexes(db, 'all_equipment')
            
            print(f"  Master collection created with {len(all_equipment)} items")
            
    except Exception as e:
        print(f"  Error creating master collection: {e}")

def upload_to_mongodb():
    """Main upload function"""
    print("PhysioTracker MongoDB Upload")
    print("=" * 40)
    
    # Connect to MongoDB
    client, db = connect_to_mongodb()
    if client is None or db is None:
        return False
    
    # Get CSV files from data folder
    data_folder = Path(__file__).parent.parent / "data"
    csv_files = list(data_folder.glob("*.csv"))
    
    if not csv_files:
        print("No CSV files found in data folder")
        client.close()
        return False
    
    print(f"\nFound {len(csv_files)} CSV files:")
    for csv_file in csv_files:
        size_kb = csv_file.stat().st_size / 1024
        print(f"  {csv_file.name} ({size_kb:.1f} KB)")
    
    total_uploaded = 0
    successful_uploads = 0
    
    print(f"\nStarting upload process...")
    
    # Process each CSV file
    for csv_file in csv_files:
        try:
            collection_name = csv_file.stem  # b301, b302, etc.
            
            print(f"\nProcessing: {csv_file.name}")
            print(f"Collection: {collection_name}")
            
            # Process CSV file
            records = process_csv_file(csv_file, collection_name)
            
            if not records:
                continue
            
            # Clear existing collection
            old_count = db[collection_name].count_documents({})
            if old_count > 0:
                db[collection_name].drop()
                print(f"  Cleared {old_count} existing documents")
            
            # Insert new data
            result = db[collection_name].insert_many(records)
            print(f"  Inserted {len(result.inserted_ids)} documents")
            
            # Create indexes
            create_indexes(db, collection_name)
            
            total_uploaded += len(result.inserted_ids)
            successful_uploads += 1
            
        except Exception as e:
            print(f"  Failed to upload {csv_file.name}: {e}")
    
    # Create master collection
    if successful_uploads > 0:
        print(f"\n" + "-" * 40)
        create_master_collection(db)
    
    # Show final summary
    print(f"\n" + "=" * 40)
    print(f"Upload Summary:")
    print(f"Files processed: {len(csv_files)}")
    print(f"Successful uploads: {successful_uploads}")
    print(f"Total documents: {total_uploaded}")
    
    if successful_uploads > 0:
        print(f"\nCollections in physiotracker_db:")
        for collection_name in sorted(db.list_collection_names()):
            count = db[collection_name].count_documents({})
            
            if count > 0:
                # Show equipment type and operational status breakdown
                try:
                    type_pipeline = [
                        {"$group": {"_id": "$equipment_type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ]
                    status_pipeline = [
                        {"$group": {"_id": "$operational_status", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ]
                    
                    type_breakdown = list(db[collection_name].aggregate(type_pipeline))
                    status_breakdown = list(db[collection_name].aggregate(status_pipeline))
                    
                    type_summary = {item['_id']: item['count'] for item in type_breakdown}
                    status_summary = {item['_id']: item['count'] for item in status_breakdown}
                    
                    print(f"  {collection_name}: {count} items")
                    print(f"    Types: {type_summary}")
                    print(f"    Status: {status_summary}")
                    
                except:
                    print(f"  {collection_name}: {count} items")
        
        print(f"\nMongoDB Compass: mongodb://localhost:27017")
        print(f"Database: physiotracker_db")
        print(f"Upload completed successfully!")
    else:
        print(f"Upload failed. Check errors above.")
    
    client.close()
    return successful_uploads > 0

def main():
    """Main function - runs upload automatically"""
    upload_to_mongodb()

if __name__ == "__main__":
    main()