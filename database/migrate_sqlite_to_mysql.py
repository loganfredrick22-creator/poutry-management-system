#!/usr/bin/env python3
"""
FarmLink SQLite to MySQL Migration Script
This script migrates data from SQLite to MySQL database.
"""

import sqlite3
import pymysql
import os
from datetime import datetime
from decimal import Decimal

# Configuration
SQLITE_DB = "farmlink.db"
MYSQL_CONFIG = {
    'host': os.environ.get('FARMLINK_MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('FARMLINK_MYSQL_PORT', 3306)),
    'user': os.environ.get('FARMLINK_MYSQL_USER', 'root'),
    'password': os.environ.get('FARMLINK_MYSQL_PASSWORD', ''),
    'database': 'farmlink',
    'charset': 'utf8mb4'
}

def migrate_data():
    """Migrate data from SQLite to MySQL"""
    print("Starting SQLite to MySQL migration...")
    
    try:
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Connect to MySQL
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
        
        print("Connected to both databases successfully!")
        
        # Migrate tables in order (respecting foreign keys)
        tables = [
            'user',
            'flock', 
            'bird',
            'health_event',
            'mortality_log',
            'weight_record',
            'egg_production',
            'audit_log'
        ]
        
        for table_name in tables:
            print(f"\nMigrating {table_name}...")
            migrate_table(sqlite_cursor, mysql_cursor, table_name)
        
        # Commit all changes
        mysql_conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'mysql_conn' in locals():
            mysql_conn.rollback()
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'mysql_conn' in locals():
            mysql_conn.close()

def migrate_table(sqlite_cursor, mysql_cursor, table_name):
    """Migrate a single table from SQLite to MySQL"""
    
    # Get data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  No data in {table_name}")
        return
    
    # Get column names
    columns = [description[0] for description in sqlite_cursor.description]
    
    # Prepare INSERT statement for MySQL
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
    
    # Convert and insert data
    migrated_count = 0
    for row in rows:
        try:
            # Convert row to dictionary and handle data types
            data = []
            for col_name, value in zip(columns, row):
                if value is None:
                    data.append(None)
                elif isinstance(value, datetime):
                    data.append(value)
                elif isinstance(value, Decimal):
                    data.append(float(value))
                else:
                    data.append(value)
            
            mysql_cursor.execute(insert_sql, data)
            migrated_count += 1
            
        except Exception as e:
            print(f"  ⚠️  Warning: Failed to migrate row {migrated_count + 1}: {e}")
            continue
    
    print(f"  ✅ Migrated {migrated_count} rows to {table_name}")

def check_sqlite_data():
    """Check if SQLite database exists and has data"""
    if not os.path.exists(SQLITE_DB):
        print(f"❌ SQLite database '{SQLITE_DB}' not found!")
        return False
    
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("❌ SQLite database has no tables!")
            return False
        
        print(f"✅ Found SQLite database with tables: {', '.join(tables)}")
        
        # Count total records
        total_records = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_records += count
            print(f"  {table}: {count} records")
        
        print(f"Total records: {total_records}")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking SQLite database: {e}")
        return False

def check_mysql_connection():
    """Test MySQL connection"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✅ MySQL connection successful! Version: {version}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return False

if __name__ == "__main__":
    print("FarmLink SQLite to MySQL Migration Tool")
    print("=" * 50)
    
    # Check prerequisites
    if not check_sqlite_data():
        print("\nPlease ensure SQLite database exists and has data.")
        exit(1)
    
    if not check_mysql_connection():
        print("\nPlease ensure MySQL server is running and accessible.")
        exit(1)
    
    # Confirm migration
    response = input("\nDo you want to proceed with migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        exit(0)
    
    # Run migration
    migrate_data()
