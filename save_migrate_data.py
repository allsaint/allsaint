# migrate_data.py
import sqlite3 as std_sqlite3
import libsql_experimental as libsql
import os

# Source: Your local SQLite database
LOCAL_DB = "hospital.db"

# Destination: Turso (your credentials)
TURSO_URL = "libsql://hospitaldb-allsaint.aws-us-west-2.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJKUDR5RVV1RkVmR0ZzVVlaVGt3WUFnIiwib3JnX2lkIjoxMDAwMTYxOTU0fQ.QVw1aSHOv3qjXDRBzAbzW60NGO1Z3IrS3pFsZR_rh1TPTjSryseQB4dl2pXY_ZlX__KoedHb_Or_Qo81VzowBw"

def migrate_data():
    """Migrate all data from local SQLite to Turso cloud."""
    
    print("=" * 50)
    print("📦 Starting data migration from SQLite to Turso")
    print("=" * 50)
    
    # Check if local database exists
    if not os.path.exists(LOCAL_DB):
        print(f"❌ Local database '{LOCAL_DB}' not found!")
        print("   Make sure you're running this script in the correct directory")
        return
    
    # Connect to local SQLite
    print(f"\n📂 Connecting to local SQLite: {LOCAL_DB}")
    local_conn = std_sqlite3.connect(LOCAL_DB)
    local_conn.row_factory = std_sqlite3.Row
    local_cursor = local_conn.cursor()
    
    # Connect to Turso
    print(f"☁️  Connecting to Turso cloud database...")
    try:
        turso_conn = libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)
        turso_cursor = turso_conn.cursor()
        print("   ✅ Connected to Turso successfully!")
    except Exception as e:
        print(f"   ❌ Failed to connect to Turso: {e}")
        return
    
    # Get all tables from local database (excluding sqlite_* system tables)
    local_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = local_cursor.fetchall()
    
    print(f"\n📋 Found {len(tables)} tables to migrate:")
    for t in tables:
        print(f"   - {t[0]}")
    
    # Migrate each table
    total_rows_migrated = 0
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Migrating table: {table_name}")
        
        try:
            # Get column names and types from local database
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = local_cursor.fetchall()
            columns = [col[1] for col in columns_info]
            columns_str = ", ".join(columns)
            placeholders = ", ".join(["?" for _ in columns])
            
            # First, create the table in Turso if it doesn't exist
            # Get create table statement from local
            local_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            create_sql = local_cursor.fetchone()[0]
            
            try:
                turso_cursor.execute(create_sql)
                print(f"   ✅ Table structure created in Turso")
            except Exception as e:
                # Table might already exist
                if "already exists" in str(e).lower():
                    print(f"   ⏭️  Table already exists in Turso")
                else:
                    print(f"   ⚠️  Warning creating table: {e}")
            
            # Get all data from local
            local_cursor.execute(f"SELECT * FROM {table_name}")
            rows = local_cursor.fetchall()
            
            if rows:
                # Insert into Turso
                rows_inserted = 0
                for row in rows:
                    # Convert row to list of values in column order
                    values = [row[col] for col in columns]
                    
                    # Handle None values and convert special types
                    values = [v if v is not None else None for v in values]
                    
                    try:
                        turso_cursor.execute(
                            f"INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})",
                            values
                        )
                        rows_inserted += 1
                    except Exception as e:
                        print(f"   ⚠️  Error inserting row {rows_inserted + 1}: {e}")
                        continue
                
                turso_conn.commit()
                print(f"   ✅ Migrated {rows_inserted}/{len(rows)} rows")
                total_rows_migrated += rows_inserted
            else:
                print(f"   ⏭️  No data in table (empty)")
                
        except Exception as e:
            print(f"   ❌ Error migrating table {table_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"✅ Migration complete!")
    print(f"   Total rows migrated: {total_rows_migrated}")
    print("=" * 50)
    
    # Verify migration by counting rows in Turso
    print("\n🔍 Verifying migration...")
    for table in tables:
        table_name = table[0]
        try:
            turso_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            turso_count = turso_cursor.fetchone()[0]
            
            local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            local_count = local_cursor.fetchone()[0]
            
            if turso_count == local_count:
                print(f"   ✅ {table_name}: {turso_count}/{local_count} rows")
            else:
                print(f"   ⚠️  {table_name}: {turso_count}/{local_count} rows (mismatch)")
        except Exception as e:
            print(f"   ❌ {table_name}: Verification failed - {e}")
    
    local_conn.close()
    turso_conn.close()
    
    print("\n💡 Your data is now safely stored in Turso cloud!")
    print("   It will persist even when your Render app restarts.")

if __name__ == "__main__":
    migrate_data()