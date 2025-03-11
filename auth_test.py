#!/usr/bin/env python3
"""
Simple script to test Bitget API authentication.
This can be used to quickly verify if your API credentials are working properly.
"""

import json
import sys
import time
from bitget.client import BitgetClient

def load_config(config_path='config.json'):
    """Load configuration from file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Invalid JSON in configuration file: {config_path}")
        sys.exit(1)

def test_authentication(config_path='config.json'):
    """Test authentication with Bitget API"""
    print("\n===== Testing Bitget API Authentication =====\n")
    
    # Load credentials from config
    config = load_config(config_path)
    credentials = config.get('api_credentials', {})
    
    # Display masked credentials for verification
    api_key = credentials.get('api_key', '')
    api_secret = credentials.get('api_secret', '')
    passphrase = credentials.get('passphrase', '')
    
    # Check for empty credentials
    if not api_key or not api_secret or not passphrase:
        print("❌ ERROR: Missing API credentials in config.json")
        print("\nPlease update your config.json file with valid API credentials:")
        print("""
    {
        "api_credentials": {
            "api_key": "your_bitget_api_key",
            "api_secret": "your_bitget_api_secret",
            "passphrase": "your_bitget_passphrase"
        },
        ...
    }
        """)
        return False
    
    print(f"API Key: {api_key[:4]}{'*' * (len(api_key) - 4)}")
    print(f"API Secret: {api_secret[:4]}{'*' * (len(api_secret) - 4)}")
    print(f"Passphrase: {passphrase[:2]}{'*' * (len(passphrase) - 2)}")
    
    # Initialize client with full debugging
    client = BitgetClient(
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        is_futures=True,
        debug=True
    )
    
    # Try to find a working endpoint and authenticate
    try:
        print("\nSearching for working Bitget API endpoints...")
        client.try_alternate_base_urls()
        
        print("\nTesting authentication...")
        auth_success = client.test_authentication()
        
        if auth_success:
            print("\n✅ Authentication successful! Your API credentials are working correctly.")
            return True
        else:
            print("\n❌ Authentication failed!")
            print("\nThe Bitget API endpoints are accessible, but authentication failed.")
            print("Please double-check your API credentials.")
            return False
            
    except Exception as e:
        print("\n❌ Authentication failed!")
        print(f"Error: {e}")
        
        print("\nTroubleshooting tips:")
        print("1. Check for whitespace in your API credentials")
        print("2. Verify you've copied the entire API key, secret, and passphrase")
        print("3. Try creating a new set of API keys on Bitget")
        print("4. Ensure your API key has trading permissions enabled")
        print("5. If using IP restrictions, verify your current IP is allowed")
        print("6. Bitget may have changed their API. Check their documentation for updates")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bitget API authentication')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug output')
    args = parser.parse_args()
    
    success = test_authentication(args.config)
    sys.exit(0 if success else 1)
