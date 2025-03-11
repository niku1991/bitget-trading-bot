#!/usr/bin/env python3
"""
Simple script to test Bitget API authentication.
This can be used to quickly verify if your API credentials are working properly.
"""

import json
import sys
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
    
    # Try the simplest API call
    try:
        # First try a server time API call
        print("\nTesting server time API call...")
        response = client._request("GET", "/market/time")
        
        print("\nServer time API call successful:")
        print(f"Response: {response}")
        
        # If successful, try an account endpoint that requires API key
        print("\nTesting account API call...")
        balance = client.get_account_balance()
        print(f"Account balance: {balance} USDT")
        
        print("\n✅ Authentication successful! Your API credentials are working correctly.")
        return True
    except Exception as e:
        print("\n❌ Authentication failed!")
        print(f"Error: {e}")
        
        print("\nTroubleshooting tips:")
        print("1. Check for whitespace in your API credentials")
        print("2. Verify you've copied the entire API key, secret, and passphrase")
        print("3. Try creating a new set of API keys on Bitget")
        print("4. Ensure your API key has trading permissions enabled")
        print("5. If using IP restrictions, verify your current IP is allowed")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bitget API authentication')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    args = parser.parse_args()
    
    success = test_authentication(args.config)
    sys.exit(0 if success else 1)
