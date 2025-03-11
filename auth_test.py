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
    print("\n===== Bitget API Authentication Test =====\n")
    
    # Load credentials from config
    config = load_config(config_path)
    credentials = config.get('api_credentials', {})
    
    # Display masked credentials for verification
    api_key = credentials.get('api_key', '')
    api_secret = credentials.get('api_secret', '')
    passphrase = credentials.get('passphrase', '')
    
    # Check for empty credentials
    if not api_key or not api_secret or not passphrase:
        print("❌ One or more API credentials are missing or empty in your config file.")
        print("Please check your config.json file and ensure all credentials are provided.")
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
    
    # Connect to the Bitget API
    if not client.ping_api():
        print("\nUnable to connect to Bitget API with initial base URL.")
        print("Attempting to find a working API endpoint...")
        
        if not client.try_alternate_base_urls():
            print("\n❌ Could not connect to any Bitget API endpoints.")
            print("This could indicate:")
            print("1. Network connectivity issues")
            print("2. Bitget's API endpoints have significantly changed")
            print("3. Bitget servers might be experiencing issues")
            return False
    
    print(f"\nUsing Bitget API base URL: {client.base_url}")
    
    # Try full authentication
    try:
        # First try to connect to a public endpoint
        print("\nTesting connection to public endpoints...")
        start_time = time.time()
        client.ping_api()
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"✅ Successfully connected to Bitget API (latency: {latency:.2f}ms)")
        
        # Now test authenticated access
        print("\nTesting authenticated API access...")
        try:
            balance = client.get_account_balance()
            print(f"✅ Authentication successful! Account balance: {balance:.6f} USDT")
            
            print("\nAdditional connection info:")
            print(f"- API Base URL: {client.base_url}")
            print(f"- Connection Latency: {latency:.2f}ms")
            
            print("\n✅ All tests passed! Your API credentials are working correctly.")
            return True
        except Exception as e:
            print(f"\n❌ Authentication failed when trying to access account information.")
            print(f"Error: {str(e)}")
            print("\nThis usually indicates:")
            print("1. Your API key, secret, or passphrase is incorrect")
            print("2. Your API key doesn't have permission to access account information")
            print("3. IP restrictions are preventing access (if enabled)")
            return False
            
    except Exception as e:
        print("\n❌ Connection to Bitget API failed!")
        print(f"Error: {str(e)}")
        
        print("\nTroubleshooting tips:")
        print("1. Check your internet connection")
        print("2. Verify Bitget services are operational (check their status page)")
        print("3. Try again later if this appears to be a temporary issue")
        return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bitget API authentication')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    args = parser.parse_args()
    
    success = test_authentication(args.config)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
