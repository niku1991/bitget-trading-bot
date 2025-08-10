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
        
        # Default base URLs - these might need to be updated based on current Bitget API structure
        if is_futures:
            self.base_url = "https://api.bitget.com/api/mix/v1"
        else:
            self.base_url = "https://api.bitget.com/api/spot/v1"
        
        self.is_futures = is_futures
        self.session = requests.Session()
    
    def try_alternate_base_urls(self):
        """
        Try different base URL formats to find the working one
        
        Returns:
        - True if a working URL was found, False otherwise
        """
        # List of possible base URLs to try
        possible_futures_urls = [
            "https://api.bitget.com/api/mix/v1",
            "https://api.bitget.com/api/mix/v2",
            "https://api.bitget.com/v2/mix",
            "https://api.bitget.com/api/futures/v3",
            "https://api-swap.bitget.com/api/swap/v3"
        ]
        
        possible_spot_urls = [
            "https://api.bitget.com/api/spot/v1",
            "https://api.bitget.com/api/spot/v2",
            "https://api.bitget.com/v2/spot"
        ]
        
        # Select which list to try based on API type
        possible_urls = possible_futures_urls if self.is_futures else possible_spot_urls
        
        if self.debug:
            print("\n===== Trying to find working Bitget API URL =====")
        
        for url in possible_urls:
            old_base = self.base_url
            self.base_url = url
            
            try:
                if self.debug:
                    print(f"\nTrying base URL: {url}")
                
                # Try two different common endpoints
                try:
                    # First try: common endpoint for market data
                    endpoint = "/market/contracts" if self.is_futures else "/market/symbols"
                    response = self._request("GET", endpoint, skip_auth=True)
                    if self.debug:
                        print(f"✅ Success with base URL: {url} using endpoint {endpoint}")
                    return True
                except Exception as e:
                    if "URL NOT FOUND" not in str(e):
                        raise e
                    
                    # Second try: time endpoint
                    endpoint = "/public/time"
                    response = self._request("GET", endpoint, skip_auth=True)
                    if self.debug:
                        print(f"✅ Success with base URL: {url} using endpoint {endpoint}")
                    return True
                    
            except Exception as e:
                if self.debug:
                    print(f"❌ Failed with base URL: {url}")
                    print(f"Error: {str(e)}")
                # Restore the original base URL
                self.base_url = old_base
        
        if self.debug:
            print("\n❌ Unable to find a working Bitget API URL")
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
    
    def _request(self, method, endpoint, params=None, data=None, skip_auth=False):
        """
        Make authenticated request to BitGet API
        
        Parameters:
        - method: HTTP method (GET, POST, etc.)
        - endpoint: API endpoint path
        - params: Query parameters for GET requests
        - data: Request body for POST requests
        - skip_auth: Whether to skip authentication (for public endpoints)
        
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
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add authentication headers if needed
        if not skip_auth:
            # Generate signature
            signature = self._generate_signature(timestamp, method, endpoint, data)
            
            # Add auth headers
            headers.update({
                'ACCESS-KEY': self.api_key,
                'ACCESS-SIGN': signature,
                'ACCESS-TIMESTAMP': timestamp,
                'ACCESS-PASSPHRASE': self.passphrase
            })
            
        # Debug logging
        if self.debug:
            print(f"\nDEBUG: Request: {method} {url}")
            print(f"DEBUG: Timestamp: {timestamp}")
            print(f"DEBUG: Headers:")
            for key, value in headers.items():
                if key == 'ACCESS-PASSPHRASE':
                    masked_value = value[:3] + '*' * (len(value) - 3)
                    print(f"  {key}: {masked_value}")
                elif key == 'ACCESS-SIGN':
                    print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")
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
                if not skip_auth and resp_json.get('code') != '00000' and 'code' in resp_json:
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

    def ping_api(self):
        """
        Test if the API is reachable via a public endpoint.

        Returns True on success, False otherwise.
        """
        try:
            endpoint = "/public/time"
            self._request("GET", endpoint, skip_auth=True)
            return True
        except Exception:
            return False

    def get_candles(self, symbol, granularity="1m", limit=200):
        """
        Fetch historical candles for a symbol.

        Parameters:
        - symbol: Trading pair symbol (e.g., "DOGEUSDT_UMCBL")
        - granularity: Candle interval. Common values: "1m", "5m", "15m", "1h", "4h", "1d"
        - limit: Number of candles to fetch (max depends on API)

        Returns:
        - List of candles where each item is a dict with keys: ts, open, high, low, close, volume
        """
        # Bitget futures market candles endpoint; API paths may vary across versions
        # This uses a commonly available path pattern consistent with other market endpoints in this client
        endpoint = "/market/candles"
        params = {"symbol": symbol, "granularity": granularity, "limit": str(limit)}
        resp = self._request("GET", endpoint, params=params, skip_auth=True)

        data = resp.get("data", [])
        normalized = []
        for item in data:
            # Support both array and dict responses to be robust to API changes
            if isinstance(item, (list, tuple)) and len(item) >= 6:
                ts, open_p, high_p, low_p, close_p, volume = item[:6]
            elif isinstance(item, dict):
                ts = item.get("ts") or item.get("timestamp")
                open_p = item.get("open")
                high_p = item.get("high")
                low_p = item.get("low")
                close_p = item.get("close")
                volume = item.get("volume")
            else:
                continue

            try:
                normalized.append({
                    "ts": int(ts),
                    "open": float(open_p),
                    "high": float(high_p),
                    "low": float(low_p),
                    "close": float(close_p),
                    "volume": float(volume)
                })
            except Exception:
                # Skip malformed entries
                continue

        # Sort ascending by timestamp
        normalized.sort(key=lambda x: x["ts"])
        return normalized

    def get_pending_orders(self):
        """
        Get pending orders
        
        Returns:
        - List of pending orders
        """
        return self._request("GET", "/order/pending")

    def cancel_order(self, symbol, order_id):
        """
        Cancel a single pending order by ID.

        Parameters:
        - symbol: Trading pair symbol
        - order_id: The order ID

        Returns API response JSON.
        """
        endpoint = "/order/cancelOrder"
        data = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "orderId": str(order_id)
        }
        return self._request("POST", endpoint, data=data)

    def cancel_all_pending_orders(self):
        """
        Cancel all currently pending orders for USDT margin.
        """
        pending = self.get_pending_orders()
        results = []
        for order in pending.get('data', []) or []:
            try:
                symbol = order.get('symbol')
                order_id = order.get('orderId') or order.get('id')
                if symbol and order_id:
                    res = self.cancel_order(symbol, order_id)
                    results.append(res)
            except Exception as e:
                results.append({"error": str(e), "order": order})
        return results
    
    def test_authentication(self):
        """
        Test API authentication
        
        Returns:
        - True if authentication is successful, False otherwise
        """
        # First try to find a working base URL
        if not self.try_alternate_base_urls():
            print("Failed to find a working Bitget API endpoint. Please check if Bitget's API structure has changed.")
            return False
            
        try:
            # Now that we have a working base URL, try to get account info
            if self.debug:
                print("\n===== Testing Authentication with Account API Call =====")
            
            response = self._request("GET", "/account/accounts", params={"productType": "umcbl"})
            print("Authentication test successful!")
            
            # Show account balance if available
            for acct in response.get('data', []):
                if acct.get('marginCoin') == 'USDT':
                    print(f"Account USDT Balance: {acct.get('available', 'N/A')}")
                    break
                    
            return True
        except Exception as e:
            print(f"Authentication test failed: {str(e)}")
            return False
