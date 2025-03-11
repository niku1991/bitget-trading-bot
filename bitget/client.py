import time
import hmac
import base64
import hashlib
import requests
import json
from urllib.parse import urlencode

class BitgetClient:
    def __init__(self, api_key, api_secret, passphrase, is_futures=True, debug=True):
        """
        Initialize the Bitget API client
        
        Parameters:
        - api_key: Your Bitget API key
        - api_secret: Your Bitget API secret
        - passphrase: Your Bitget API passphrase
        - is_futures: Whether to use futures API (True) or spot API (False)
        - debug: Whether to enable debug output
        """
        self.api_key = api_key.strip()  # Strip to remove any whitespace
        self.api_secret = api_secret.strip()
        self.passphrase = passphrase.strip()
        self.debug = debug
        
        # Base URL for API endpoints - Bitget regularly updates their API paths
        self.is_futures = is_futures
        
        # We'll try multiple possible base URLs, starting with the most likely ones
        if is_futures:
            # USDT-M Futures (also called USDT Swap/Perpetual)
            self.base_url = "https://api.bitget.com/api/mix/v1"
        else:
            # Spot trading
            self.base_url = "https://api.bitget.com/api/spot/v1"
            
        self.session = requests.Session()
    
    def try_alternate_base_urls(self):
        """
        Try different base URL formats to find the working one
        
        Returns:
        - True if a working base URL was found, False otherwise
        """
        if self.is_futures:
            # Possible futures/mix/swap API base URLs
            possible_urls = [
                "https://api.bitget.com/api/mix/v1",
                "https://api.bitget.com/api/mix/v2",
                "https://api.bitget.com/v2/mix",
                "https://api.bitget.com/api/swap/v3",
                "https://api-swap.bitget.com/api/swap/v3",
                "https://api.bitget.com/api/futures/v3"
            ]
        else:
            # Possible spot API base URLs
            possible_urls = [
                "https://api.bitget.com/api/spot/v1",
                "https://api.bitget.com/api/spot/v2",
                "https://api.bitget.com/v2/spot",
                "https://api-cloud.bitget.com/api/spot/v1"
            ]
        
        original_base = self.base_url
        original_debug = self.debug
        
        # Temporarily enable debug if it wasn't already
        self.debug = True
        
        print(f"\nTrying to find working Bitget API endpoint...")
        for url in possible_urls:
            self.base_url = url
            try:
                # Try different common public endpoints
                endpoints_to_try = [
                    "/market/contracts",  # Futures contract info
                    "/market/tickers",    # All tickers info
                    "/market/time",       # Server time
                    "/public/time",       # Alternative server time
                    "/public/products"    # Product info
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        print(f"Trying {url}{endpoint}...")
                        response = self.session.get(f"{url}{endpoint}")
                        
                        if response.status_code == 200:
                            print(f"✅ Success with {url}{endpoint}")
                            # Restore original debug setting
                            self.debug = original_debug
                            return True
                        else:
                            print(f"❌ Failed with {url}{endpoint}: {response.status_code}")
                    except Exception as e:
                        print(f"❌ Error with {url}{endpoint}: {str(e)}")
                        continue
            except Exception as e:
                print(f"❌ Failed with base URL {url}: {str(e)}")
                continue
        
        # If we didn't find a working URL, restore the original
        self.base_url = original_base
        self.debug = original_debug
        print(f"❌ Could not find working Bitget API endpoint. Using {self.base_url}")
        return False
    
    def _generate_signature(self, timestamp, method, request_path, body=''):
        """
        Generate BitGet signature for API authentication
        
        Parameters:
        - timestamp: Current timestamp in milliseconds
        - method: HTTP method (GET, POST, etc.)
        - request_path: API endpoint path
        - body: Request body (for POST requests)
        
        Returns:
        - Base64 encoded signature
        """
        # For empty body, use empty string instead of JSON
        body_str = json.dumps(body) if body else ''
        
        # Construct the message (method must be uppercase)
        message = str(timestamp) + method.upper() + request_path + body_str
        
        if self.debug:
            print(f"DEBUG: Signature message: {message}")
            
        # Generate the HMAC-SHA256 signature
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return signature
    
    def _request(self, method, endpoint, params=None, data=None):
        """
        Make authenticated request to BitGet API
        
        Parameters:
        - method: HTTP method (GET, POST, etc.)
        - endpoint: API endpoint path
        - params: Query parameters for GET requests
        - data: Request body for POST requests
        
        Returns:
        - API response as JSON
        """
        url = self.base_url + endpoint
        timestamp = str(int(time.time() * 1000))
        
        # Add query parameters to URL if provided
        query_string = ""
        if params:
            query_string = urlencode(params)
            url = url + '?' + query_string
            
        # Generate signature
        signature = self._generate_signature(timestamp, method, endpoint, data)
        
        # Prepare headers
        headers = {
            'ACCESS-KEY': self.api_key,
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        # Debug logging
        if self.debug:
            print(f"\nDEBUG: Request: {method} {url}")
            print(f"DEBUG: Timestamp: {timestamp}")
            print(f"DEBUG: Headers:")
            print(f"  ACCESS-KEY: {self.api_key}")
            print(f"  ACCESS-SIGN: {signature}")
            print(f"  ACCESS-TIMESTAMP: {timestamp}")
            print(f"  ACCESS-PASSPHRASE: {self.passphrase[:3]}{'*' * (len(self.passphrase) - 3)}")  # Show only first 3 chars
            if data:
                print(f"DEBUG: Data: {json.dumps(data)}")
        
        # Make request
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data
            )
            
            # Debug response
            if self.debug:
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response body: {response.text[:2000]}")  # Limit to 2000 chars
            
            # Handle response
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get('code') != '00000' and 'code' in resp_json:
                    error_message = f"API request failed: {response.text}"
                    print(error_message)
                    raise Exception(error_message)
                return resp_json
            # Handle 404 errors specifically - might need to try different base URLs
            elif response.status_code == 404:
                error_message = f"API endpoint not found (404): {response.text}"
                print(error_message)
                print("This may indicate that Bitget's API structure has changed.")
                raise Exception(error_message)
            else:
                error_message = f"API request failed: {response.text}"
                print(error_message)
                raise Exception(error_message)
                
        except requests.exceptions.RequestException as e:
            error_message = f"Request error: {str(e)}"
            print(error_message)
            raise Exception(error_message)
    
    # Utility methods
    def ping_api(self):
        """
        Check if the API is accessible with a simple public endpoint
        
        Returns:
        - True if successful, False otherwise
        """
        try:
            # Try several common public endpoints that don't require authentication
            endpoints = [
                "/market/contracts",
                "/market/tickers",
                "/public/time"
            ]
            
            for endpoint in endpoints:
                try:
                    url = self.base_url + endpoint
                    if self.debug:
                        print(f"Pinging API with: GET {url}")
                    
                    response = self.session.get(url)
                    
                    if response.status_code == 200:
                        if self.debug:
                            print(f"API ping successful with {endpoint}")
                        return True
                except Exception:
                    continue
            
            return False
        except Exception as e:
            if self.debug:
                print(f"API ping failed: {str(e)}")
            return False
    
    # Trading methods
    def place_order(self, symbol, side, order_type, price=None, size=None, leverage=None):
        """
        Place an order on Bitget Futures
        
        Parameters:
        - symbol: Trading pair symbol (e.g., "DOGEUSDT_UMCBL")
        - side: Order side ("buy" or "sell")
        - order_type: Order type ("limit" or "market")
        - price: Order price (required for limit orders)
        - size: Order size in contracts
        - leverage: Trading leverage
        
        Returns:
        - Order response from API
        """
        endpoint = "/order/placeOrder"
        
        # Prepare order data
        data = {
            "symbol": symbol,         # e.g., "DOGEUSDT_UMCBL"
            "marginCoin": "USDT",     # Margin currency
            "side": side,             # "buy" or "sell"
            "orderType": order_type,  # "limit" or "market"
            "size": str(size)         # Contract quantity
        }
        
        # Add price for limit orders
        if order_type == "limit" and price is not None:
            data["price"] = str(price)
            
        # Set leverage if provided
        if leverage is not None:
            self.set_leverage(symbol, leverage)
            
        return self._request("POST", endpoint, data=data)
    
    def set_leverage(self, symbol, leverage):
        """
        Set leverage for a symbol
        
        Parameters:
        - symbol: Trading pair symbol (e.g., "DOGEUSDT_UMCBL")
        - leverage: Leverage value (e.g., 10)
        
        Returns:
        - API response
        """
        endpoint = "/account/setLeverage"
        data = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "leverage": str(leverage)
        }
        return self._request("POST", endpoint, data=data)
    
    def get_positions(self, symbol=None):
        """
        Get current positions
        
        Parameters:
        - symbol: (Optional) Trading pair symbol to filter positions
        
        Returns:
        - List of current positions
        """
        endpoint = "/position/allPosition"
        params = {"marginCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", endpoint, params=params)
    
    def place_stop_order(self, symbol, side, size, trigger_price, price=None):
        """
        Place stop order (stop loss or take profit)
        
        Parameters:
        - symbol: Trading pair symbol (e.g., "DOGEUSDT_UMCBL")
        - side: Order side ("buy" or "sell")
        - size: Order size in contracts
        - trigger_price: Price at which to trigger the order
        - price: (Optional) Execution price for limit orders
        
        Returns:
        - Order response from API
        """
        endpoint = "/plan/placePlan"
        data = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "side": side,
            "size": str(size),
            "triggerPrice": str(trigger_price),
            "triggerType": "market_price",
            "orderType": "market" if price is None else "limit"
        }
        
        if price is not None:
            data["executePrice"] = str(price)
            
        return self._request("POST", endpoint, data=data)
    
    def get_market_price(self, symbol):
        """
        Get current market price for a symbol
        
        Parameters:
        - symbol: Trading pair symbol (e.g., "DOGEUSDT_UMCBL")
        
        Returns:
        - Current market price as float
        """
        endpoint = "/market/ticker"
        params = {"symbol": symbol}
        response = self._request("GET", endpoint, params=params)
        return float(response['data']['last'])
    
    def get_account_balance(self):
        """
        Get account balance
        
        Returns:
        - Available USDT balance
        """
        response = self._request("GET", "/account/accounts", params={"productType": "umcbl"})
        for acct in response['data']:
            if acct['marginCoin'] == 'USDT':
                return float(acct['available'])
        return 0.0
    
    def get_pending_orders(self):
        """
        Get pending orders
        
        Returns:
        - List of pending orders
        """
        return self._request("GET", "/order/pending")
    
    def test_authentication(self):
        """
        Test API authentication
        
        Returns:
        - True if authentication is successful, False otherwise
        """
        print("\n===== Testing Bitget API Connection =====")
        
        # First try to find a working API endpoint if needed
        if not self.ping_api():
            print("Unable to connect to API with current base URL. Trying to find working URL...")
            if not self.try_alternate_base_urls():
                print("❌ Could not find a working Bitget API endpoint.")
                return False
        
        print(f"Using API base URL: {self.base_url}")
        
        # Now test authentication with the working base URL
        try:
            # Try to get server contracts as a simple API call that requires authentication
            response = self._request("GET", "/market/contracts")
            print("✅ Authentication test successful!")
            return True
        except Exception as e:
            print(f"❌ Authentication test failed: {str(e)}")
            
            # Provide troubleshooting tips
            print("\nTroubleshooting tips:")
            print("1. Check your API key, secret, and passphrase for accuracy")
            print("2. Ensure there's no whitespace in your credentials")
            print("3. Check if your API key has the necessary permissions")
            print("4. If you've enabled IP restrictions, ensure your current IP is allowed")
            print("5. Try creating new API credentials on Bitget")
            return False
