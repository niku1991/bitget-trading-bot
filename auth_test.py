#!/usr/bin/env python3
"""
Enhanced script to test Bitget API authentication.
This script tries multiple API endpoints and base URLs to find working combinations.
"""

import json
import sys
import requests
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

def try_direct_public_request():
    """Try making direct unauthenticated requests to various Bitget API endpoints"""
    print("\n===== Testing Direct Public API Endpoints =====")
    
    endpoints = [
        # Mix/Futures public endpoints
        "https://api.bitget.com/api/mix/v1/market/contracts?productType=umcbl",
        "https://api.bitget.com/api/mix/v1/market/tickers?productType=umcbl",
        "https://api.bitget.com/api/mix/v1/market/time",
        
        # Newer V2 API endpoints
        "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",
        "https://api.bitget.com/api/v2/spot/public/time",
        
        # Spot public endpoints
        "https://api.bitget.com/api/spot/v1/market/tickers",
        "https://api.bitget.com/api/spot/v1/public/time"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Trying: {endpoint}")
            response = requests.get(endpoint, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Success!")
                print(f"Response: {response.text[:200]}...\n")
                return endpoint.split("/market")[0] if "/market" in endpoint else endpoint.rsplit("/", 1)[0]
            else:
                print(f"❌ Failed: {response.text[:200]}...\n")
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")
    
    return None

def test_authentication(config_path='config.json'):
    """Test authentication with Bitget API using multiple approaches"""
    print("\n===== Testing Bitget API Authentication =====\n")
    
    # First check if we can reach Bitget's API at all
    print("Checking Bitget API availability...")
    try:
        response = requests.get("https://api.bitget.com/api/mix/v1/market/contracts?productType=umcbl", timeout=10)
        if response.status_code != 200:
            print("Cannot connect to Bitget API. Let's try direct public endpoints first...")
            working_base_url = try_direct_public_request()
            if working_base_url:
                print(f"Found a working Bitget API base URL: {working_base_url}")
            else:
                print("Could not find any working Bitget API endpoints. Please check your internet connection.")
                return False
    except Exception as e:
        print(f"Error connecting to Bitget API: {str(e)}")
        print("Let's try direct public endpoints...")
        working_base_url = try_direct_public_request()
        if working_base_url:
            print(f"Found a working Bitget API base URL: {working_base_url}")
        else:
            print("Could not find any working Bitget API endpoints. Please check your internet connection.")
            return False
    
    # Load credentials from config
    config = load_config(config_path)
    credentials = config.get('api_credentials', {})
    
    # Display masked credentials for verification
    api_key = credentials.get('api_key', '')
    api_secret = credentials.get('api_secret', '')
    passphrase = credentials.get('passphrase', '')
    
    print(f"API Key: {api_key[:6]}{'*' * (len(api_key) - 6)}")
    print(f"API Secret: {api_secret[:6]}{'*' * (len(api_secret) - 6)}")
    print(f"Passphrase: {passphrase[:2]}{'*' * (len(passphrase) - 2)}")
    
    # Check for credential issues
    if not api_key or not api_secret or not passphrase:
        print("❌ Error: Missing API credentials in config.json")
        return False
    
    # Initialize client with full debugging
    client = BitgetClient(
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        is_futures=True,
        debug=True
    )
    
    # Test authentication
    if client.test_authentication():
        print("\n✅ Authentication successful! Your API credentials are working correctly.")
        return True
    else:
        print("\n❌ Authentication failed!")
        
        print("\nTroubleshooting tips:")
        print("1. Check for whitespace in your API credentials")
        print("2. Verify you've copied the entire API key, secret, and passphrase")
        print("3. Try creating a new set of API keys on Bitget")
        print("4. Ensure your API key has trading permissions enabled")
        print("5. If using IP restrictions, verify your current IP is allowed")
        print("6. Make sure your system clock is correctly synchronized")
        
        # Provide info about the specific error if possible
        print("\nAdditional diagnostics:")
        print("- Bitget API documentation: https://bitgetlimited.github.io/apidoc/en/mix/")
        print("- Check if Bitget's API status page reports any issues")
        print("- Consider using the Bitget API v2 if v1 is deprecated")
        print("- Try using a VPN if your location might be restricted")
        
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bitget API authentication')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    args = parser.parse_args()
    
    success = test_authentication(args.config)
    sys.exit(0 if success else 1)
