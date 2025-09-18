#!/usr/bin/env python3
"""
Complete setup script for the quote generation system.
This script will:
1. Check environment variables
2. Run database migrations
3. Backfill embeddings
4. Run tests
"""

import os
import asyncio
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()


def check_environment():
    """Check if required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = ['OPENAI_API_KEY', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set these in your .env file or environment:")
        for var in missing_vars:
            print(f"  {var}=your_value_here")
        return False
    
    print("✅ Environment variables are set")
    return True


def run_script(script_path, description):
    """Run a Python script and return success status."""
    print(f"\n🚀 {description}...")
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False


def main():
    """Main setup process."""
    print("🎯 Setting up IP Protect Quote Generation System")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    # Run migrations
    if not run_script("scripts/run_migrations.py", "Running database migrations"):
        print("\n⚠️  Migration failed. Please check your database connection and try again.")
        return 1
    
    # Backfill embeddings
    if not run_script("scripts/backfill_embeddings.py", "Backfilling product embeddings"):
        print("\n⚠️  Embedding backfill failed. Please check your OpenAI API key and try again.")
        return 1
    
    # Run tests
    if not run_script("scripts/test_quote_api.py", "Running system tests"):
        print("\n⚠️  Some tests failed. Please check the output above for details.")
        print("You may still be able to use the system, but some features might not work correctly.")
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Start the server: python main.py")
    print("2. Test the API: Use the requests in http/quote.http")
    print("3. Check the API docs: http://localhost:8000/docs")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
