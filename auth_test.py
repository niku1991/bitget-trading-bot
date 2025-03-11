#!/usr/bin/env python3
"""
Advanced Bitget API Authentication Test Script.

This script attempts to find working API endpoints and verify your Bitget API credentials.
It will try multiple possible API URLs and endpoints to accommodate API changes by Bitget.
"""

import json
import sys
import argparse
from bitget.client import BitgetClient

def load_config(config_path='config.json'):
    """
    Load configuration from file
    
    Parameters:
    - config_path: Path to configuration file
    
    Returns:
    - Config dictionary or None if error
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        print(f"Please make sure '{config_path}' exists in the current directory.")
        return None
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in configuration file: {config_path}")
        print("Please check that your config file contains valid JSON.")
        return None

def show_credentials_summary(credentials):
    """
    Display masked credentials for verification
    
    Parameters:
    - credentials: Dictionary containing API credentials
    """
    api_key = credentials.get('api_key', '')
    api_secret = credentials.get('api_secret', '')
    passphrase = credentials.get('passphrase', '')
    
    print("\n===== API Credentials Summary =====")
    if not api_key or not api_secret or not passphrase:
        print("❌ One or more required credentials are missing!")
    
    # Show masked credentials
    if api_key:
        print(f"API Key: {api_key[:4]}{'*' * (len(api_key) - 4)}")
    else:
        print("❌ API Key: Missing")
        
    if api_secret:
        print(f"API Secret: {api_secret[:4]}{'*' * (len(api_secret) - 4)}")
    else:
        print("❌ API Secret: Missing")
        
    if passphrase:
        print(f"Passphrase: {passphrase[:2]}{'*' * (len(passphrase) - 2)}")
    else:
        print("❌ Passphrase: Missing")

def test_authentication(config_path='config.json', debug=True, futures=True):
    """
    Comprehensive authentication test with multiple URLs and endpoints
    
    Parameters:
    - config_path: Path to configuration file
    - debug: Whether to enable debug output
    - futures: Whether to test futures API (True) or spot API (False)
    
    Returns:
    - True if authentication succeeds, False otherwise
    """
    print("\n===== Bitget API Advanced Authentication Test =====")
    print(f"Testing {'futures' if futures else 'spot'} API endpoints")
    
    # Load configuration
    config = load_config(config_path)
    if not config:
        return False
    
    # Extract credentials
    credentials = config.get('api_credentials', {})
    api_key = credentials.get('api_key', '').strip()
    api_secret = credentials.get('api_secret', '').strip()
    passphrase = credentials.get('passphrase', '').strip()
    
    # Verify credentials are present
    if not api_key or not api_secret or not passphrase:
        print("❌ Missing API credentials in config file.")
        print("Please update your config.json with complete API credentials.")
        return False
    
    # Display credentials summary
    show_credentials_summary(credentials)
    
    # Initialize Bitget client
    print("\n===== Initializing API Client =====")
    client = BitgetClient(
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        is_futures=futures,
        debug=debug
    )
    
    # Run the comprehensive authentication test
    auth_success = client.test_authentication()
    
    if auth_success:
        print("\n===== Recommendations =====")
        print("✅ Authentication successful! Your API setup is working correctly.")
        print("You can now run the trading bot with:")
        print("    python main.py")
        return True
    else:
        print("\n===== Next Steps =====")
        print("1. Check Bitget's official API documentation for any changes")
        print("2. Create new API keys on Bitget and update your config.json")
        print("3. Ensure your network can access Bitget's API servers")
        print("4. Try running the test with the spot API option:")
        print("    python auth_test.py --spot")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced Bitget API Authentication Test')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug output')
    parser.add_argument('--spot', action='store_true', help='Test spot API instead of futures API')
    args = parser.parse_args()
    
    success = test_authentication(
        config_path=args.config,
        debug=not args.no_debug,
        futures=not args.spot
    )
    
    sys.exit(0 if success else 1)
