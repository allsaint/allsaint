# migrate_to_sqlitecloud.py
import sqlite3 as std_sqlite3
import sqlitecloud
import os

# Source: Your local SQLite database
LOCAL_DB = "hospital.db"

# Destination: SQLite Cloud (YOUR connection string)
SQLITECLOUD_CONNECTION = "sqlitecloud://cwo2lzaavk.g4.sqlite.cloud:8860/auth.sqlitecloud?apikey=dezQi8ib8nxJ5lRM9TpIaoOMNNo4IaHSCU3mxokDFRM"

def migrate_data():
    """Migrate all data from local SQLite to SQLite Cloud."""
    
    print("=" * 50)
    print("📦 Migrating data to SQLite Cloud")
    print("=" * 50)
    
    # Check if local database exists
    if not os.path.exists(LOCAL_DB):
        print(f"❌ Local database '{LOCAL_DB}' not found!")
        print("   Make sure you're in the correct directory")
        return
    
    # Connect to local SQLite
    print(f"\n📂 Reading from local SQLite: {LOCAL_DB}")
    local_conn = std_sqlite3.connect(LOCAL_DB)
    local_conn.row_factory = std_sqlite3.Row
    local_cursor = local_conn.cursor()
    
    # Connect to SQLite Cloud
    print(f"☁️  Connecting to SQLite Cloud...")
    try:
        cloud_conn = sqlitecloud.connect(SQLITECLOUD_CONNECTION)
        cloud_conn.row_factory = sqlitecloud.Row
        cloud_cursor = cloud_conn.cursor()
        print("   ✅ Connected to SQLite Cloud!")
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        print("\n   Troubleshooting:")
        print("   1. Check your internet connection")
        print("   2. Verify the connection string is correct")
        print("   3. Make sure sqlitecloud is installed: pip install sqlitecloud")
        return
    
    # Get all tables from local database
    local_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = local_cursor.fetchall()
    
    print(f"\n📋 Found {len(tables)} tables to migrate")
    
    total_rows_migrated = 0
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Migrating table: {table_name}")
        
        try:
            # Get create table statement
            local_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            create_sql = local_cursor.fetchone()[0]
            
            # Create table in SQLite Cloud (if not exists)
            try:
                cloud_cursor.execute(create_sql)
                cloud_conn.commit()
                print(f"   ✅ Table structure created")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ⏭️  Table already exists")
                else:
                    print(f"   ⚠️  Warning creating table: {str(e)[:100]}")
            
            # Get column names
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in local_cursor.fetchall()]
            
            if not columns:
                print(f"   ⚠️  No columns found, skipping")
                continue
                
            columns_str = ", ".join(columns)
            placeholders = ", ".join(["?" for _ in columns])
            
            # Get all data from local
            local_cursor.execute(f"SELECT * FROM {table_name}")
            rows = local_cursor.fetchall()
            
            if rows:
                rows_inserted = 0
                for row in rows:
                    values = [row[col] for col in columns]
                    
                    # Skip if all values are None
                    if all(v is None for v in values):
                        continue
                    
                    # Build INSERT statement
                    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})"
                    
                    try:
                        cloud_cursor.execute(insert_sql, values)
                        rows_inserted += 1
                        if rows_inserted % 10 == 0:
                            print(f"   📍 Migrated {rows_inserted}/{len(rows)} rows...")
                    except Exception as e:
                        error_msg = str(e)[:80]
                        if "UNIQUE constraint" in error_msg:
                            # Skip duplicates silently
                            rows_inserted += 1
                        else:
                            print(f"   ⚠️  Error: {error_msg}")
                        continue
                
                cloud_conn.commit()
                print(f"   ✅ Migrated {rows_inserted}/{len(rows)} rows")
                total_rows_migrated += rows_inserted
            else:
                print(f"   ⏭️  No data in table")
                
        except Exception as e:
            print(f"   ❌ Error migrating {table_name}: {str(e)[:100]}")
    
    local_conn.close()
    cloud_conn.close()
    
    print("\n" + "=" * 50)
    print(f"✅ Migration complete!")
    print(f"   Total rows migrated: {total_rows_migrated}")
    print("=" * 50)
    
    # Verify migration
    verify_migration()

def verify_migration():
    """Verify data was migrated correctly."""
    print("\n🔍 Verifying migration...")
    
    local_conn = std_sqlite3.connect(LOCAL_DB)
    local_cursor = local_conn.cursor()
    cloud_conn = sqlitecloud.connect(SQLITECLOUD_CONNECTION)
    cloud_cursor = cloud_conn.cursor()
    
    local_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = local_cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        try:
            # Get count from local
            local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            local_count = local_cursor.fetchone()[0]
            
            if local_count == 0:
                continue
            
            # Get count from SQLite Cloud
            cloud_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            cloud_count = cloud_cursor.fetchone()[0]
            
            if local_count == cloud_count:
                print(f"   ✅ {table_name}: {cloud_count}/{local_count} rows")
            else:
                print(f"   ⚠️  {table_name}: {cloud_count}/{local_count} rows (mismatch)")
        except Exception as e:
            print(f"   ❌ {table_name}: Verification failed - {e}")
    
    local_conn.close()
    cloud_conn.close()

def test_connection():
    """Test SQLite Cloud connection."""
    print("Testing SQLite Cloud connection...")
    try:
        conn = sqlitecloud.connect(SQLITECLOUD_CONNECTION)
        cursor = conn.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print("✅ SQLite Cloud connection successful!")
        print(f"   Test result: {result[0]}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("\n🚀 SQLite Cloud Migration Tool")
    print("-" * 50)
    
    # Test connection first
    if not test_connection():
        print("\n❌ Cannot proceed with migration.")
        print("\nPlease check:")
        print("1. Your connection string is correct")
        print("2. You have internet access")
        print("3. The sqlitecloud package is installed: pip install sqlitecloud")
        exit(1)
    
    # Ask for confirmation
    print(f"\n📁 Local database: {LOCAL_DB}")
    if not os.path.exists(LOCAL_DB):
        print(f"❌ Local database not found at: {os.path.abspath(LOCAL_DB)}")
        exit(1)
    
    print(f"   Size: {os.path.getsize(LOCAL_DB) / 1024:.1f} KB")
    
    confirm = input("\n⚠️  This will migrate ALL data to SQLite Cloud. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        migrate_data()
    else:
        print("Migration cancelled.")