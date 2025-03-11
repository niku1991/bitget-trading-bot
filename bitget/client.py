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
        self.is_futures = is_futures
        
        # Set initial base URL (may be updated by try_alternate_base_urls)
        self._set_base_url(is_futures)
        
        self.session = requests.Session()
    
    def _set_base_url(self, is_futures):
        """Set the base URL based on API type"""
        if is_futures:
            # Current futures/mix API URL as of March 2025
            self.base_url = "https://api.bitget.com/api/mix/v1"
        else:
            # Current spot API URL as of March 2025
            self.base_url = "https://api.bitget.com/api/spot/v1"
    
    def try_alternate_base_urls(self):
        """
        Try different base URL formats to find the working one
        
        Returns:
        - True if a working URL was found, False otherwise
        """
        # Potential base URLs for the Bitget API (updated for 2025)
        possible_urls = [
            # Current and previous formats
            "https://api.bitget.com/api/mix/v1",
            "https://api.bitget.com/api/swap/v3",
            "https://api.bitget.com/api/v2/mix",
            "https://api.bitget.com/v2/mix",
            "https://api-swap.bitget.com/api/swap/v3",
            "https://api.bitget.com/api/futures/v3"
        ]
        
        # Store original base URL
        original_base_url = self.base_url
        success = False
        
        for url in possible_urls:
            self.base_url = url
            if self.debug:
                print(f"\nTrying base URL: {url}")
            
            # List of endpoints to try
            test_endpoints = [
                "/market/contracts",
                "/public/time",
                "/market/time", 
                "/public/products"
            ]
            
            for endpoint in test_endpoints:
                try:
                    # Try to fetch a simple public endpoint
                    response = self._request("GET", endpoint, auth_required=False)
                    if self.debug:
                        print(f"✅ Success with base URL: {url} and endpoint: {endpoint}")
                    # If successful, keep this base URL and return
                    return True
                except Exception as e:
                    if self.debug:
                        print(f"Failed with endpoint {endpoint}: {str(e)}")
                    continue  # Try next endpoint
        
        # If all attempts failed, restore the original base URL
        self.base_url = original_base_url
        if self.debug:
            print(f"❌ Could not find a working API endpoint. Reverting to {original_base_url}")
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
    
    def _request(self, method, endpoint, params=None, data=None, auth_required=True):
        """
        Make request to BitGet API
        
        Parameters:
        - method: HTTP method (GET, POST, etc.)
        - endpoint: API endpoint path
        - params: Query parameters for GET requests
        - data: Request body for POST requests
        - auth_required: Whether authentication is required for this request
        
        Returns:
        - API response as JSON
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        url = self.base_url + endpoint
        timestamp = str(int(time.time() * 1000))
        
        # Add query parameters to URL if provided
        query_string = ""
        if params:
            query_string = urlencode(params)
            url = url + '?' + query_string
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'BitgetTradingBot/1.0'
        }
        
        # Add authentication headers if required
        if auth_required:
            # Generate signature
            signature = self._generate_signature(timestamp, method, endpoint, data)
            
            # Add auth headers
            headers.update({
                'ACCESS-KEY': self.api_key,
                'ACCESS-SIGN': signature,
                'ACCESS-TIMESTAMP': timestamp,
                'ACCESS-PASSPHRASE': self.passphrase,
            })
        
        # Debug logging
        if self.debug:
            print(f"\nDEBUG: Request: {method} {url}")
            print(f"DEBUG: Timestamp: {timestamp}")
            if auth_required:
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
                if resp_json.get('code') != '00000' and 'code' in resp_json and resp_json.get('code') != 0:
                    error_message = f"API request failed: {response.text}"
                    print(error_message)
                    raise Exception(error_message)
                return resp_json
            else:
                error_message = f"API request failed: {response.text}"
                print(error_message)
                raise Exception(error_message)
                
        except requests.exceptions.RequestException as e:
            error_message = f"Request error: {str(e)}"
            print(error_message)
            raise Exception(error_message)
    
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
        try:
            # First try to find a working base URL
            if not self.try_alternate_base_urls():
                print("Could not find a working API endpoint. Authentication test failed.")
                return False
                
            # Now try to get account balance which requires authentication
            print("Testing authenticated endpoint...")
            balance = self.get_account_balance()
            print(f"Authentication test successful! Account balance: {balance} USDT")
            return True
        except Exception as e:
            print(f"Authentication test failed: {str(e)}")
            return False
