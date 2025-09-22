#!/usr/bin/env python3
"""
Script to run database migrations locally
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if required environment variables are set."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        print("   Please set it in your .env file")
        return False
    
    # Mask credentials in output
    masked_url = database_url.replace(database_url.split('@')[0].split('//')[1], '***')
    print(f"✅ Database URL configured: {masked_url}")
    return True

def run_alembic_command(command):
    """Run an alembic command and return success status."""
    try:
        print(f"🚀 Running: alembic {command}")
        result = subprocess.run(
            ["alembic"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running alembic {command}:")
        print(e.stdout)
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Error: Alembic not found. Install it with: pip install alembic")
        return False

def main():
    """Main migration runner."""
    print("🔧 Database Migration Runner")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check if alembic is available
    try:
        subprocess.run(["alembic", "--help"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Alembic not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "alembic"], check=True)
    
    print("\n📋 Available migration commands:")
    print("1. Show current revision")
    print("2. Show migration history")
    print("3. Upgrade to latest migration (recommended)")
    print("4. Upgrade to specific revision")
    print("5. Downgrade to previous revision")
    print("6. Show pending migrations")
    
    choice = input("\nChoose an option (1-6) or press Enter for option 3: ").strip()
    
    if not choice:
        choice = "3"
    
    success = True
    
    if choice == "1":
        success = run_alembic_command("current")
    elif choice == "2":
        success = run_alembic_command("history")
    elif choice == "3":
        print("\n🔄 Upgrading database to latest version...")
        success = run_alembic_command("upgrade head")
    elif choice == "4":
        revision = input("Enter revision ID: ").strip()
        if revision:
            success = run_alembic_command(f"upgrade {revision}")
        else:
            print("❌ No revision specified")
            success = False
    elif choice == "5":
        success = run_alembic_command("downgrade -1")
    elif choice == "6":
        print("\n📋 Checking for pending migrations...")
        # Show current and head
        run_alembic_command("current")
        run_alembic_command("heads")
    else:
        print("❌ Invalid choice")
        success = False
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("\n📊 Current database status:")
        run_alembic_command("current -v")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()