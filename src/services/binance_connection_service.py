"""
Binance Connection Service
Handles connection testing and validation for Binance API credentials
"""

import asyncio
import hashlib
import hmac
import logging
import ssl
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
import certifi

logger = logging.getLogger(__name__)


class BinanceConnectionService:
    """Service for testing and validating Binance API connections."""

    # Binance API endpoints
    MAINNET_BASE_URL = "https://api.binance.com"
    TESTNET_BASE_URL = "https://testnet.binance.vision"

    # Futures endpoints
    MAINNET_FUTURES_URL = "https://fapi.binance.com"
    TESTNET_FUTURES_URL = "https://testnet.binancefuture.com"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=connector,
            headers={
                "User-Agent": "Kamikaze-Trader/1.0",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _generate_signature(self, query_string: str, secret_key: str) -> str:
        """Generate HMAC SHA256 signature for Binance API."""
        return hmac.new(
            secret_key.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _get_base_url(self, is_testnet: bool, use_futures: bool = False) -> str:
        """Get the appropriate base URL for the environment."""
        if use_futures:
            return self.TESTNET_FUTURES_URL if is_testnet else self.MAINNET_FUTURES_URL
        else:
            return self.TESTNET_BASE_URL if is_testnet else self.MAINNET_BASE_URL

    async def _make_request(
        self,
        endpoint: str,
        api_key: str,
        secret_key: str = None,
        params: Dict[str, Any] = None,
        is_testnet: bool = False,
        use_futures: bool = False,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Make authenticated request to Binance API."""
        if not self.session:
            raise Exception("Session not initialized. Use async context manager.")

        base_url = self._get_base_url(is_testnet, use_futures)
        url = f"{base_url}{endpoint}"

        headers = {"X-MBX-APIKEY": api_key}

        # Prepare parameters
        if params is None:
            params = {}

        # Add timestamp for signed requests
        if signed:
            params["timestamp"] = int(time.time() * 1000)

            # Create query string and signature
            query_string = urlencode(params)
            signature = self._generate_signature(query_string, secret_key)
            params["signature"] = signature

        try:
            async with self.session.get(
                url, params=params, headers=headers
            ) as response:
                data = await response.json()

                if response.status == 200:
                    return {
                        "success": True,
                        "data": data,
                        "status_code": response.status,
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("msg", f"HTTP {response.status}"),
                        "error_code": data.get("code"),
                        "status_code": response.status,
                    }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timeout",
                "error_code": "TIMEOUT",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "error_code": "CONNECTION_ERROR"}

    async def test_connection(
        self, api_key: str, secret_key: str, is_testnet: bool = False
    ) -> Dict[str, Any]:
        """Test Binance API connection and return account information."""
        try:
            # Test 1: Server time (no authentication required)
            server_time_result = await self._make_request(
                "/api/v3/time", api_key, is_testnet=is_testnet
            )

            if not server_time_result["success"]:
                return {
                    "success": False,
                    "message": "Failed to connect to Binance servers",
                    "error": server_time_result["error"],
                    "error_code": server_time_result.get("error_code"),
                }

            # Test 2: Account information (requires authentication)
            account_result = await self._make_request(
                "/api/v3/account",
                api_key,
                secret_key,
                is_testnet=is_testnet,
                signed=True,
            )

            if not account_result["success"]:
                error_code = account_result.get("error_code")
                error_msg = account_result["error"]

                # Provide specific guidance based on error code
                if error_code == -2015:
                    detailed_msg = (
                        f"Authentication failed: {error_msg}\n\n"
                        "🔧 SOLUTION:\n"
                        f"1. Check your {'Testnet' if is_testnet else 'Mainnet'} API key permissions\n"
                        "2. Ensure 'Enable Spot & Margin Trading' is checked\n"
                        "3. Verify your IP address is whitelisted (or use 'Unrestricted' for testing)\n"
                        f"4. Confirm you're using {'TESTNET' if is_testnet else 'MAINNET'} credentials\n\n"
                        f"📋 Binance {'Testnet' if is_testnet else 'Mainnet'} API Management:\n"
                        f"{'https://testnet.binance.vision/' if is_testnet else 'https://www.binance.com/en/my/settings/api-management'}"
                    )
                elif error_code == -1021:
                    detailed_msg = (
                        f"Timestamp error: {error_msg}. Please check your system clock."
                    )
                elif error_code == -1022:
                    detailed_msg = (
                        f"Signature error: {error_msg}. Please check your secret key."
                    )
                else:
                    detailed_msg = f"Authentication failed: {error_msg}"

                return {
                    "success": False,
                    "message": detailed_msg,
                    "error": error_msg,
                    "error_code": error_code,
                }

            account_data = account_result["data"]

            # Test 3: Get API key permissions
            permissions = []
            if account_data.get("canTrade"):
                permissions.append("SPOT_TRADING")
            if account_data.get("canWithdraw"):
                permissions.append("WITHDRAW")
            if account_data.get("canDeposit"):
                permissions.append("DEPOSIT")

            # Test 4: Try futures account (optional)
            futures_enabled = False
            try:
                futures_result = await self._make_request(
                    "/fapi/v2/account",
                    api_key,
                    secret_key,
                    is_testnet=is_testnet,
                    use_futures=True,
                    signed=True,
                )
                if futures_result["success"]:
                    futures_enabled = True
                    permissions.append("FUTURES_TRADING")
            except Exception:
                pass  # Futures not enabled or accessible

            # Extract key account information
            balances = []
            for balance in account_data.get("balances", []):
                free_balance = float(balance["free"])
                locked_balance = float(balance["locked"])
                if free_balance > 0 or locked_balance > 0:
                    balances.append(
                        {
                            "asset": balance["asset"],
                            "free": free_balance,
                            "locked": locked_balance,
                            "total": free_balance + locked_balance,
                        }
                    )

            return {
                "success": True,
                "message": f'Successfully connected to Binance {"Testnet" if is_testnet else "Mainnet"}',
                "account_info": {
                    "account_type": account_data.get("accountType", "SPOT"),
                    "can_trade": account_data.get("canTrade", False),
                    "can_withdraw": account_data.get("canWithdraw", False),
                    "can_deposit": account_data.get("canDeposit", False),
                    "futures_enabled": futures_enabled,
                    "balances": balances[:10],  # Limit to top 10 non-zero balances
                    "total_balances": len(balances),
                },
                "permissions": permissions,
                "environment": "testnet" if is_testnet else "mainnet",
                "server_time": server_time_result["data"]["serverTime"],
            }

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "message": "Connection test failed",
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR",
            }

    async def validate_api_key_format(
        self, api_key: str, is_testnet: bool = False
    ) -> Tuple[bool, str]:
        """Validate API key format."""
        if not api_key:
            return False, "API key is required"

        # Remove whitespace
        api_key = api_key.strip()

        # Basic length validation
        if len(api_key) < 32:
            return False, "API key too short"

        if len(api_key) > 128:
            return False, "API key too long"

        # Testnet keys are typically longer and have different patterns
        if is_testnet:
            if len(api_key) < 32 or len(api_key) > 128:
                return False, "Testnet API key should be 32-128 characters"
        else:
            # Mainnet keys are typically 64 characters
            if len(api_key) != 64:
                return False, "Mainnet API key should be exactly 64 characters"

        # Check for valid characters (alphanumeric)
        if not api_key.replace("-", "").replace("_", "").isalnum():
            return False, "API key contains invalid characters"

        return True, "Valid API key format"

    async def validate_secret_key_format(self, secret_key: str) -> Tuple[bool, str]:
        """Validate secret key format."""
        if not secret_key:
            return False, "Secret key is required"

        # Remove whitespace
        secret_key = secret_key.strip()

        # Basic length validation
        if len(secret_key) < 32:
            return False, "Secret key too short"

        if len(secret_key) > 128:
            return False, "Secret key too long"

        # Check for valid base64-like characters
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        )
        if not all(c in valid_chars for c in secret_key):
            return False, "Secret key should be base64 encoded"

        return True, "Valid secret key format"

    async def get_account_status(
        self, api_key: str, secret_key: str, is_testnet: bool = False
    ) -> Dict[str, Any]:
        """Get detailed account status and trading permissions."""
        try:
            # Get account information
            account_result = await self._make_request(
                "/api/v3/account",
                api_key,
                secret_key,
                is_testnet=is_testnet,
                signed=True,
            )

            if not account_result["success"]:
                return account_result

            account_data = account_result["data"]

            # Get trading status
            trading_status = await self._make_request(
                "/sapi/v1/account/status",
                api_key,
                secret_key,
                is_testnet=is_testnet,
                signed=True,
            )

            status_data = (
                trading_status.get("data", {}) if trading_status["success"] else {}
            )

            return {
                "success": True,
                "account_type": account_data.get("accountType"),
                "trading_enabled": account_data.get("canTrade", False),
                "withdrawal_enabled": account_data.get("canWithdraw", False),
                "deposit_enabled": account_data.get("canDeposit", False),
                "account_status": status_data.get("data", "Unknown"),
                "maker_commission": account_data.get("makerCommission", 0),
                "taker_commission": account_data.get("takerCommission", 0),
                "buyer_commission": account_data.get("buyerCommission", 0),
                "seller_commission": account_data.get("sellerCommission", 0),
                "update_time": account_data.get("updateTime"),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "STATUS_CHECK_FAILED",
            }


# Global service instance
binance_service = BinanceConnectionService()
