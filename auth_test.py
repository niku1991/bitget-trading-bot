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
    
    # First attempt to find a working API endpoint
    if not client.try_alternate_base_urls():
        print("\n❌ Failed to find a working Bitget API endpoint.")
        print("Please check if Bitget has changed their API structure.")
        print("Visit Bitget's developer documentation for the latest API information.")
        return False
    
    # Now try authentication
    try:
        # Try an account endpoint that requires API key
        print("\n===== Testing account API call with authentication =====")
        response = client._request("GET", "/account/accounts", params={"productType": "umcbl"})
        
        print("\nAccount API call successful:")
        print(f"Response: {str(response)[:500]}...")  # Truncate for readability
        
        # Show account balance if available
        for acct in response.get('data', []):
            if acct.get('marginCoin') == 'USDT':
                print(f"\nAccount USDT Balance: {acct.get('available', 'N/A')}")
                break
        
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
        
        # Suggest inspecting error details
        if "40012" in str(e):
            print("\nThe error '40012' (apikey/password is incorrect) suggests:")
            print("- Your API key or passphrase is not recognized by Bitget")
            print("- Your credentials might be from a different Bitget account")
            print("- Your API key might have been deleted or expired")
        elif "40009" in str(e):
            print("\nThe error '40009' (sign signature error) suggests:")
            print("- Your API secret might be incorrect")
            print("- Your system time might be out of sync with Bitget's servers")
            print("- There might be encoding or invisible character issues with your secret")
        elif "40404" in str(e):
            print("\nThe error '40404' (URL not found) suggests:")
            print("- Bitget may have changed their API structure")
            print("- The API endpoint being used might be deprecated")
            print("- You might need to use a different API version")
        
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bitget API authentication')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable even more detailed debug output')
    args = parser.parse_args()
    
    success = test_authentication(args.config)
    sys.exit(0 if success else 1)
