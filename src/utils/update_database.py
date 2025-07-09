"""Update database schema to add banking features"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import pymysql
from sqlalchemy import text
from src.payment_service.api import create_app
from src.models.payment_models import db

def update_payments_table():
    """Add bank_account_id column to payments table"""
    try:
        app = create_app('development')
        
        with app.app_context():
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('payments')]
            
            if 'bank_account_id' in columns:
                print("✓ Column bank_account_id already exists")
                return True
            
            # Add the missing column using proper SQLAlchemy 2.x syntax
            with db.engine.connect() as connection:
                # Add the column
                connection.execute(text("""
                    ALTER TABLE payments 
                    ADD COLUMN bank_account_id VARCHAR(36) NULL
                """))
                
                # Add index for better performance
                connection.execute(text("""
                    CREATE INDEX idx_payments_bank_account 
                    ON payments(bank_account_id)
                """))
                
                # Commit the transaction
                connection.commit()
            
            print("✓ Successfully added bank_account_id column to payments table")
            
    except Exception as e:
        if "Duplicate column name" in str(e):
            print("✓ Column bank_account_id already exists")
        elif "Duplicate key name" in str(e):
            print("✓ Index idx_payments_bank_account already exists")
        else:
            print(f"Error updating payments table: {e}")
            return False
    return True

def create_banking_tables():
    """Create banking tables"""
    try:
        app = create_app('development')
        
        with app.app_context():
            # Import banking models to ensure they're registered
            from src.models.banking_models import BankAccount, AccountTransaction
            
            # Create all tables
            db.create_all()
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            banking_tables = ['bank_accounts', 'account_transactions']
            created_banking_tables = [table for table in banking_tables if table in tables]
            
            print(f"✓ Banking tables created: {created_banking_tables}")
            
    except Exception as e:
        print(f"Error creating banking tables: {e}")
        return False
    return True

def verify_database_schema():
    """Verify the complete database schema"""
    try:
        app = create_app('development')
        
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print("\n📊 Database Schema Verification:")
            print("=" * 40)
            
            required_tables = {
                'payments': ['id', 'merchant_id', 'customer_id', 'amount', 'currency', 'bank_account_id'],
                'bank_accounts': ['id', 'account_number', 'customer_id', 'current_balance'],
                'account_transactions': ['id', 'account_id', 'transaction_type', 'amount'],
                'refunds': ['id', 'payment_id', 'amount'],
                'transactions': ['id', 'payment_id', 'transaction_type']
            }
            
            all_good = True
            for table_name, required_columns in required_tables.items():
                if table_name in tables:
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    missing_columns = [col for col in required_columns if col not in columns]
                    
                    if missing_columns:
                        print(f"❌ Table '{table_name}': Missing columns {missing_columns}")
                        all_good = False
                    else:
                        print(f"✅ Table '{table_name}': All required columns present")
                else:
                    print(f"❌ Table '{table_name}': Not found")
                    all_good = False
            
            if all_good:
                print("\n🎉 Database schema is complete and ready!")
            else:
                print("\n⚠️ Database schema has issues that need to be resolved")
            
            return all_good
            
    except Exception as e:
        print(f"Error verifying database schema: {e}")
        return False

def reset_database_if_needed():
    """Reset database if there are major schema issues"""
    try:
        app = create_app('development')
        
        print("\n🔄 Checking if database reset is needed...")
        
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            # Check if we have any tables at all
            if not tables:
                print("No tables found. Creating fresh database...")
                db.create_all()
                return True
            
            # Check for critical missing tables
            critical_tables = ['payments', 'bank_accounts']
            missing_critical = [table for table in critical_tables if table not in tables]
            
            if missing_critical:
                print(f"Missing critical tables: {missing_critical}")
                print("Creating missing tables...")
                db.create_all()
                return True
            
            print("✓ Database structure looks good")
            return True
            
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

if __name__ == "__main__":
    print("🏦 Payment System Database Schema Update")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = project_root / '.env'
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print(f"Please create .env file in: {env_file}")
        sys.exit(1)
    
    try:
        # Step 1: Reset/create database if needed
        print("\n📋 Step 1: Checking database structure...")
        if not reset_database_if_needed():
            print("❌ Failed to initialize database")
            sys.exit(1)
        
        # Step 2: Create banking tables
        print("\n📋 Step 2: Creating banking tables...")
        if not create_banking_tables():
            print("❌ Failed to create banking tables")
            sys.exit(1)
        
        # Step 3: Update payments table
        print("\n📋 Step 3: Updating payments table...")
        if not update_payments_table():
            print("❌ Failed to update payments table")
            sys.exit(1)
        
        # Step 4: Verify everything
        print("\n📋 Step 4: Verifying database schema...")
        if verify_database_schema():
            print("\n🎉 Database schema update completed successfully!")
            print("\nNext steps:")
            print("1. Start the server: python run_server.py")
            print("2. Generate sample data: python src\\utils\\sample_data.py")
            print("3. Test the API: curl http://localhost:5000/health")
        else:
            print("\n⚠️ Database schema verification failed")
            print("You may need to manually check your database")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Database update cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during database update: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check if MySQL is running")
        print("2. Verify .env file has correct database credentials")
        print("3. Make sure database exists")
        sys.exit(1)