#!/usr/bin/env python3

import os
import sys
sys.path.append('.')

# Test if .env file is loaded
print("Current working directory:", os.getcwd())
print("Contents of .env file:")
try:
    with open('.env', 'r') as f:
        print(f.read())
except FileNotFoundError:
    print(".env file not found in current directory")

# Test loading settings
from app.config import settings

print("\nLoaded settings:")
print(f"Database URL: {settings.database_url}")
print(f"API Host: {settings.api_host}")
print(f"API Port: {settings.api_port}")
print(f"Debug: {settings.debug}")

# Test environment variables directly
print("\nEnvironment variables:")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
print(f"API_HOST: {os.getenv('API_HOST')}")
print(f"DEBUG: {os.getenv('DEBUG')}")
