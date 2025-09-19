#!/usr/bin/env python3
"""Database initialization script for local development"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade
import psycopg2
from psycopg2 import sql

def wait_for_db(database_url, max_retries=30):
    """Wait for database to be available"""
    import time
    retries = 0
    while retries < max_retries:
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            print("✅ Database is ready")
            return True
        except psycopg2.OperationalError:
            retries += 1
            print(f"⏳ Waiting for database... ({retries}/{max_retries})")
            time.sleep(1)
    
    print("❌ Database not available after maximum retries")
    return False

def setup_migrations():
    """Initialize Flask-Migrate if needed"""
    if not os.path.exists('migrations'):
        print("🔧 Initializing database migrations...")
        init()
        print("✅ Migrations initialized")
    else:
        print("✅ Migrations directory already exists")

def create_migration():
    """Create a new migration if there are model changes"""
    try:
        print("🔧 Creating migration for model changes...")
        migrate(message='Auto migration')
        print("✅ Migration created")
        return True
    except Exception as e:
        print(f"ℹ️  No migration needed or error: {e}")
        return False

def apply_migrations():
    """Apply all pending migrations"""
    try:
        print("🔧 Applying database migrations...")
        upgrade()
        print("✅ Database migrations applied")
        return True
    except Exception as e:
        print(f"❌ Error applying migrations: {e}")
        return False

if __name__ == "__main__":
    # Import app after setting up the path
    from app import app, db
    
    with app.app_context():
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        if database_url.startswith('postgresql://'):
            print("🐘 Using PostgreSQL database")
            if not wait_for_db(database_url):
                sys.exit(1)
            
            # Setup migrations
            setup_migrations()
            
            # Create migration if needed
            create_migration()
            
            # Apply migrations
            apply_migrations()
            
        else:
            print("📁 Using SQLite database")
            # For SQLite, just create tables
            db.create_all()
            print("✅ SQLite tables created")
        
        print("🎉 Database setup complete!")