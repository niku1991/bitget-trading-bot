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
        
        # Updated Bitget API base URLs - we'll use the V2 API which is more recent
        if is_futures:
            # USDT-M perpetual contracts - switched to v2 API which is more reliable
            self.base_url = "https://api.bitget.com/api/v2/mix"
        else:
            # Spot trading - switched to v2 API
            self.base_url = "https://api.bitget.com/api/v2/spot"
            
        self.session = requests.Session()
        
        if debug:
            print(f"Initialized Bitget client with API key: {self.api_key[:6]}{'*' * (len(self.api_key) - 6)}")
            print(f"Using API base URL: {self.base_url}")
    
    def try_alternate_base_urls(self):
        """Try different base URL formats to find the working one"""
        possible_urls = [
            # New V2 API endpoints (preferred)
            "https://api.bitget.com/api/v2/mix",
            "https://api.bitget.com/api/v2/spot",
            "https://api.bitget.com/v2",
            
            # Legacy V1 API endpoints
            "https://api.bitget.com/api/mix/v1",
            "https://api-swap.bitget.com/api/mix/v1",
            "https://capi.bitget.com/api/swap/v3",
            "https://api.bitget.com/api/futures/v3"
        ]
        
        for url in possible_urls:
            old_base = self.base_url
            self.base_url = url
            try:
                if self.debug:
                    print(f"\nTrying base URL: {url}")
                
                # Try different endpoint formats based on the API version
                if "v2" in url:
                    # V2 API endpoints
                    if "mix" in url:
                        test_url = f"{url}/market/tickers?productType=USDT-FUTURES"
                    else:
                        test_url = f"{url}/public/time"
                else:
                    # V1 API endpoints
                    if "mix" in url or "swap" in url or "futures" in url:
                        test_url = f"{url}/market/contracts?productType=umcbl"
                    else:
                        test_url = f"{url}/public/time"
                
                # Try to fetch a simple public endpoint that doesn't require authentication
                response = self._make_public_request("GET", test_url)
                if response and response.status_code == 200:
                    print(f"✅ Success with base URL: {url}")
                    # If successful, keep this base URL
                    return True
            except Exception as e:
                if self.debug:
                    print(f"❌ Failed with base URL: {url}")
                    print(f"Error: {str(e)}")
            # Restore the original base URL
            self.base_url = old_base
        
        return False
    
    def _make_public_request(self, method, url, params=None):
        """Make a public request without authentication"""
        try:
            if params:
                if "?" in url:
                    url = url + "&" + urlencode(params)
                else:
                    url = url + "?" + urlencode(params)
            
            if self.debug:
                print(f"Making public request: {method} {url}")
                
            response = self.session.request(method, url, timeout=10)  # Added timeout
            
            if self.debug:
                print(f"Response status: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text[:2000]}")  # Limit to 2000 chars
                    
            return response
        except Exception as e:
            if self.debug:
                print(f"Public request error: {str(e)}")
            return None
    
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
        
        # Extract path from request_path (remove query parameters)
        if '?' in request_path:
            path = request_path.split('?')[0]
        else:
            path = request_path
            
        # Construct the message (method must be uppercase)
        message = str(timestamp) + method.upper() + path + body_str
        
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
        # Construct URL
        url = self.base_url + endpoint
        timestamp = str(int(time.time() * 1000))
        
        # Add query parameters to URL if provided
        query_string = ""
        if params:
            query_string = urlencode(params)
            url = url + '?' + query_string
        
        # Complete request path for signature (including query string)
        request_path = endpoint
        if query_string:
            request_path = endpoint + '?' + query_string
            
        # Generate signature
        signature = self._generate_signature(timestamp, method, request_path, data)
        
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
                json=data,
                timeout=10  # Added timeout
            )
            
            # Debug response
            if self.debug:
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response body: {response.text[:2000]}")  # Limit to 2000 chars
            
            # Handle response
            if response.status_code == 200:
                resp_json = response.json()
                if isinstance(resp_json, dict) and resp_json.get('code') != '00000' and 'code' in resp_json:
                    if resp_json.get('code') == '40404':  # URL not found
                        raise Exception(f"API endpoint not found: {endpoint}. Please check Bitget API documentation for the correct endpoint.")
                    error_message = f"API request failed: {response.text}"
                    print(error_message)
                    raise Exception(error_message)
                return resp_json
            elif response.status_code == 404:
                # Special handling for 404 errors
                error_message = f"API endpoint not found: {endpoint}. Please check Bitget API documentation for the correct endpoint."
                print(error_message)
                raise Exception(f"API request failed: {response.text}")
            else:
                error_message = f"API request failed: {response.text}"
                print(error_message)
                raise Exception(error_message)
                
        except requests.exceptions.RequestException as e:
            error_message = f"Request error: {str(e)}"
            print(error_message)
            raise Exception(error_message)
    
    # Trading methods - these need to be adapted for V2 API if we're using that
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
        # V2 API endpoint for order placement
        if "v2" in self.base_url:
            endpoint = "/order"
        else:
            # V1 API endpoint
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
        # V2 API endpoint for setting leverage
        if "v2" in self.base_url:
            endpoint = "/account/leverage"
        else:
            # V1 API endpoint
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
        # V2 API endpoint for positions
        if "v2" in self.base_url:
            endpoint = "/position/all-position"
        else:
            # V1 API endpoint
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
        # V2 API endpoint for stop orders
        if "v2" in self.base_url:
            endpoint = "/plan/place-plan"
        else:
            # V1 API endpoint
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
        # V2 API endpoint for ticker
        if "v2" in self.base_url:
            endpoint = "/market/ticker"
        else:
            # V1 API endpoint
            endpoint = "/market/ticker"
            
        params = {"symbol": symbol}
        try:
            response = self._request("GET", endpoint, params=params)
            # V2 API response structure might be different
            if "v2" in self.base_url:
                return float(response['data']['last'])
            else:
                return float(response['data']['last'])
        except Exception as e:
            print(f"Error getting market price: {str(e)}")
            print("Trying alternative endpoint...")
            
            # Try alternative endpoint for market price
            try:
                # Try public ticker endpoint which doesn't require authentication
                url = f"https://api.bitget.com/api/v2/mix/market/ticker?symbol={symbol}"
                response = self._make_public_request("GET", url)
                if response and response.status_code == 200:
                    data = response.json()
                    return float(data['data']['last'])
                return 0.0
            except Exception:
                return 0.0
    
    def get_account_balance(self):
        """
        Get account balance
        
        Returns:
        - Available USDT balance
        """
        try:
            # V2 API endpoint for account balance
            if "v2" in self.base_url:
                endpoint = "/account/accounts"
            else:
                # V1 API endpoint
                endpoint = "/account/accounts"
                
            params = {"productType": "umcbl"}
            response = self._request("GET", endpoint, params=params)
            
            for acct in response['data']:
                if acct['marginCoin'] == 'USDT':
                    return float(acct['available'])
            return 0.0
        except Exception as e:
            print(f"Error getting account balance: {str(e)}")
            if self.debug:
                print("Trying alternative endpoints...")
            
            # Try alternative endpoints
            try:
                # Try V2 endpoint
                old_base = self.base_url
                self.base_url = "https://api.bitget.com/api/v2"
                response = self._request("GET", "/mix/account/accounts", params={"productType": "umcbl"})
                self.base_url = old_base
                
                for acct in response['data']:
                    if acct['marginCoin'] == 'USDT':
                        return float(acct['available'])
            except Exception:
                self.base_url = old_base
                print("Failed to get account balance with alternative endpoint")
                
            return 0.0
    
    def get_pending_orders(self):
        """
        Get pending orders
        
        Returns:
        - List of pending orders
        """
        # V2 API endpoint for pending orders
        if "v2" in self.base_url:
            endpoint = "/order/open-order"
        else:
            # V1 API endpoint
            endpoint = "/order/pending"
            
        return self._request("GET", endpoint)
    
    def test_authentication(self):
        """
        Test API authentication
        
        Returns:
        - True if authentication is successful, False otherwise
        """
        try:
            # First try if we need to find a working base URL
            if self.debug:
                print("Testing different API base URLs...")
            if self.try_alternate_base_urls():
                print("Found working API base URL.")
            
            # Try a simple public endpoint first to ensure the base URL is correct
            print("\nTesting public API endpoint...")
            
            # Different endpoints based on API version
            if "v2" in self.base_url:
                if "mix" in self.base_url:
                    contracts_endpoint = "/market/tickers"
                    params = {"productType": "USDT-FUTURES"}
                else:
                    contracts_endpoint = "/public/time"
                    params = {}
            else:
                contracts_endpoint = "/market/contracts"
                params = {"productType": "umcbl"}
            
            public_url = self.base_url + contracts_endpoint
            public_response = self._make_public_request("GET", public_url, params)
            
            if not public_response or public_response.status_code != 200:
                print(f"Public API endpoint test failed. Status: {public_response.status_code if public_response else 'None'}")
                print("Trying other public endpoints...")
                
                # Try alternative public endpoints
                alt_endpoints = [
                    "/market/time",
                    "/public/time",
                    "/market/ticker",
                    "/public/products"
                ]
                
                for endpoint in alt_endpoints:
                    try:
                        print(f"Trying public endpoint: {endpoint}")
                        public_url = self.base_url + endpoint
                        public_response = self._make_public_request("GET", public_url)
                        if public_response and public_response.status_code == 200:
                            print(f"Public endpoint {endpoint} works!")
                            break
                    except Exception:
                        continue
            
            # Now try authenticated endpoint
            print("\nTesting authenticated API endpoint...")
            try:
                # Try to access account endpoint that requires authentication
                # Different endpoints based on API version
                if "v2" in self.base_url:
                    account_endpoint = "/account/accounts"
                else:
                    account_endpoint = "/account/accounts"
                    
                account_response = self._request("GET", account_endpoint, params={"productType": "umcbl"})
                print("Authentication test successful!")
                return True
            except Exception as e:
                print(f"Authentication test failed: {str(e)}")
                
                print("\nTrying alternative authenticated endpoints...")
                alt_auth_endpoints = [
                    ["/position/all-position", {"marginCoin": "USDT"}],
                    ["/position/allPosition", {"marginCoin": "USDT"}],
                    ["/account/getAccount", {"marginCoin": "USDT", "symbol": "BTCUSDT_UMCBL"}],
                    ["/market/symbol-level", {"symbol": "BTCUSDT_UMCBL"}]
                ]
                
                for endpoint, params in alt_auth_endpoints:
                    try:
                        print(f"Trying authenticated endpoint: {endpoint}")
                        auth_response = self._request("GET", endpoint, params=params)
                        print(f"Authentication successful with endpoint {endpoint}!")
                        return True
                    except Exception:
                        continue
                        
                return False
        except Exception as e:
            print(f"Authentication test failed: {str(e)}")
            return False
