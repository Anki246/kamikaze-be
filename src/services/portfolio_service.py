"""
Portfolio Service for FluxTrader
Manages portfolio data, calculations, and real-time updates with Binance integration
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ..infrastructure.credentials_database import credentials_db
from ..services.binance_connection_service import binance_service

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for managing portfolio data and calculations."""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 120  # 2 minutes cache for regular requests (increased to prevent rate limiting)
        self.realtime_cache_ttl = 30  # 30 seconds cache for real-time requests (increased to prevent rate limiting)
        self.last_update = {}
        self.user_locks = {}  # Per-user locks to prevent concurrent requests
        self.price_changes_cache = {}  # Cache for 24hr price changes
        self.price_changes_last_update = None
        self.rate_limit_until = {}  # Track rate limit bans per user
        self.request_count = {}  # Track request count per user
        self.request_window_start = {}  # Track request window start time

    async def get_portfolio_metrics(
        self, user_id: int, realtime: bool = False, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Get complete portfolio metrics for a user."""
        try:
            # Check if user is rate limited
            if self._is_rate_limited(user_id):
                logger.warning(f"User {user_id} is rate limited, using cached data")
                cache_key = f"portfolio_{user_id}"
                if cache_key in self.cache:
                    return self.cache[cache_key]
                else:
                    # Return mock data if no cache available during rate limit
                    return self._get_mock_portfolio_data()

            # Check cache first (unless force refresh is requested)
            cache_key = f"portfolio_{user_id}"
            if not force_refresh and self._is_cache_valid(cache_key, realtime):
                logger.debug(f"Using cached portfolio data for user {user_id}")
                return self.cache[cache_key]

            # Check request rate limiting
            if not self._can_make_request(user_id):
                logger.warning(
                    f"Request rate limit reached for user {user_id}, using cached data"
                )
                if cache_key in self.cache:
                    return self.cache[cache_key]
                else:
                    return self._get_mock_portfolio_data()

            # Use per-user lock to prevent concurrent requests for the same user
            if user_id not in self.user_locks:
                self.user_locks[user_id] = asyncio.Lock()

            async with self.user_locks[user_id]:
                # Double-check cache after acquiring lock
                if self._is_cache_valid(cache_key, realtime):
                    logger.debug(
                        f"Using cached portfolio data for user {user_id} (after lock)"
                    )
                    return self.cache[cache_key]

                # Get user credentials
                credentials = await self._get_user_credentials(user_id)
                if not credentials:
                    raise Exception("No Binance credentials found for user")

                # Get account balances
                balances = await self._get_account_balances(credentials)

                # Get current prices for all assets
                prices = await self._get_current_prices(balances)

                # Calculate portfolio metrics
                portfolio_data = await self._calculate_portfolio_metrics(
                    balances, prices
                )

            logger.debug(
                f"Portfolio data calculated for user {user_id}: {portfolio_data.get('total_value_usd', 0):.2f} USD"
            )

            # Cache the result
            self.cache[cache_key] = portfolio_data
            self.last_update[cache_key] = datetime.now(timezone.utc)

            logger.info(
                f"Portfolio metrics calculated for user {user_id}: ${portfolio_data['total_value_usd']:.2f}"
            )
            return portfolio_data

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Failed to get portfolio metrics for user {user_id}: {error_msg}"
            )

            # Check if it's a rate limit error
            if "banned until" in error_msg or "request weight" in error_msg.lower():
                self._handle_rate_limit_error(user_id, error_msg)
                # Return cached data if available during rate limit
                cache_key = f"portfolio_{user_id}"
                if cache_key in self.cache:
                    logger.info(
                        f"Returning cached data for rate-limited user {user_id}"
                    )
                    return self.cache[cache_key]
                else:
                    logger.info(f"Returning mock data for rate-limited user {user_id}")
                    return self._get_mock_portfolio_data()

            raise Exception(f"Failed to get portfolio data: {error_msg}")

    async def _get_user_credentials(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's Binance credentials."""
        try:
            # Try mainnet first, then testnet
            credentials = await credentials_db.get_binance_credentials(
                user_id, is_mainnet=True
            )
            if not credentials:
                credentials = await credentials_db.get_binance_credentials(
                    user_id, is_mainnet=False
                )

            if credentials:
                # Credentials are already decrypted by get_binance_credentials method
                return {
                    "api_key": credentials["api_key"],
                    "secret_key": credentials["secret_key"],
                    "is_testnet": not credentials["is_mainnet"],
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            return None

    async def _get_account_balances(
        self, credentials: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get account balances from Binance (both spot and futures)."""
        try:
            # Create a new service instance for this request
            service = binance_service.__class__()
            async with service:
                balances = []

                # Get spot account balances
                spot_result = await service._make_request(
                    "/api/v3/account",
                    credentials["api_key"],
                    credentials["secret_key"],
                    is_testnet=credentials["is_testnet"],
                    signed=True,
                )

                if not spot_result["success"]:
                    raise Exception(
                        f"Failed to get spot account data: {spot_result['error']}"
                    )

                # Process spot balances
                for balance in spot_result["data"]["balances"]:
                    free = float(balance["free"])
                    locked = float(balance["locked"])
                    total = free + locked

                    if total > 0:
                        balances.append(
                            {
                                "asset": balance["asset"],
                                "free": free,
                                "locked": locked,
                                "total": total,
                                "account_type": "spot",
                            }
                        )

                logger.debug(f"Retrieved {len(balances)} non-zero spot balances")

                # Get futures account balances (USDT-M)
                try:
                    futures_result = await service._make_request(
                        "/fapi/v2/account",
                        credentials["api_key"],
                        credentials["secret_key"],
                        is_testnet=credentials["is_testnet"],
                        use_futures=True,
                        signed=True,
                    )

                    if futures_result["success"]:
                        futures_balances_count = 0

                        # Process futures wallet balances
                        for asset_data in futures_result["data"]["assets"]:
                            wallet_balance = float(asset_data["walletBalance"])

                            if wallet_balance > 0:
                                # Check if we already have this asset from spot
                                existing_balance = None
                                for existing in balances:
                                    if (
                                        existing["asset"] == asset_data["asset"]
                                        and existing["account_type"] == "spot"
                                    ):
                                        existing_balance = existing
                                        break

                                if existing_balance:
                                    # Combine with existing spot balance
                                    existing_balance["futures_balance"] = wallet_balance
                                    existing_balance["total"] += wallet_balance
                                    existing_balance["account_type"] = "combined"
                                else:
                                    # Add as new futures-only balance
                                    balances.append(
                                        {
                                            "asset": asset_data["asset"],
                                            "free": wallet_balance,
                                            "locked": 0.0,
                                            "total": wallet_balance,
                                            "account_type": "futures",
                                            "futures_balance": wallet_balance,
                                        }
                                    )

                                futures_balances_count += 1

                        logger.debug(
                            f"Retrieved {futures_balances_count} non-zero futures balances"
                        )
                    else:
                        logger.warning(
                            f"Failed to get futures account data: {futures_result.get('error', 'Unknown error')}"
                        )

                except Exception as e:
                    logger.warning(
                        f"Futures account not accessible or error occurred: {e}"
                    )
                    # Continue without futures data - not all accounts have futures enabled

                total_balances = len(balances)
                logger.info(
                    f"Retrieved {total_balances} total non-zero balances (spot + futures)"
                )
                return balances

        except Exception as e:
            logger.error(f"Failed to get account balances: {e}")
            raise

    async def _get_current_prices(
        self, balances: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Get current USD prices for all assets."""
        try:
            prices = {}

            # Get symbols for price lookup
            symbols = []
            for balance in balances:
                asset = balance["asset"]
                if asset == "USDT":
                    prices[asset] = 1.0  # USDT is always $1
                elif asset == "USDC":
                    prices[asset] = 1.0  # USDC is always $1
                elif asset == "BUSD":
                    prices[asset] = 1.0  # BUSD is always $1
                else:
                    symbols.append(f"{asset}USDT")

            if symbols:
                # Get prices from Binance
                service = binance_service.__class__()
                async with service:
                    for symbol in symbols:
                        try:
                            ticker_result = await service._make_request(
                                f"/api/v3/ticker/price?symbol={symbol}",
                                "",  # No API key needed for public endpoint
                                is_testnet=False,  # Use mainnet for price data
                            )

                            if ticker_result["success"]:
                                asset = symbol.replace("USDT", "")
                                prices[asset] = float(ticker_result["data"]["price"])

                        except Exception as e:
                            logger.warning(f"Failed to get price for {symbol}: {e}")
                            # Set default price if we can't get it
                            asset = symbol.replace("USDT", "")
                            prices[asset] = 0.0

            logger.debug(f"Retrieved prices for {len(prices)} assets")
            return prices

        except Exception as e:
            logger.error(f"Failed to get current prices: {e}")
            raise

    async def _calculate_portfolio_metrics(
        self, balances: List[Dict[str, Any]], prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate portfolio metrics from balances and prices."""
        try:
            total_value_usd = 0.0
            total_value_btc = 0.0
            asset_allocation = []

            # Get BTC price for BTC value calculation
            btc_price_usd = prices.get("BTC", 0.0)

            # Get 24hr price changes for individual assets
            asset_price_changes = await self._get_asset_price_changes()
            logger.info(
                f"Asset price changes retrieved: {len(asset_price_changes)} assets"
            )

            # Debug: Log price changes for user's assets
            user_assets = [balance["asset"] for balance in balances]
            for asset in user_assets:
                change = asset_price_changes.get(asset, "NOT_FOUND")
                logger.info(f"Price change for {asset}: {change}%")

            # Calculate value for each asset
            for balance in balances:
                asset = balance["asset"]
                total_balance = balance["total"]
                price_usd = prices.get(asset, 0.0)

                # Use higher precision for calculations
                usd_value = float(Decimal(str(total_balance)) * Decimal(str(price_usd)))
                btc_value = (
                    float(Decimal(str(usd_value)) / Decimal(str(btc_price_usd)))
                    if btc_price_usd > 0
                    else 0.0
                )

                total_value_usd += usd_value
                total_value_btc += btc_value

                if usd_value > 0:  # Only include assets with value
                    # Get 24hr price change for this asset
                    price_change_24h = asset_price_changes.get(asset, 0.0)
                    logger.info(
                        f"Asset {asset}: price_change_24h = {price_change_24h}% (from asset_price_changes)"
                    )

                    asset_allocation.append(
                        {
                            "asset": asset,
                            "balance": total_balance,
                            "usd_value": usd_value,
                            "btc_value": btc_value,
                            "percentage": 0.0,  # Will be calculated after total
                            "price_change_24h": price_change_24h,
                        }
                    )

            # Calculate percentages
            for allocation in asset_allocation:
                allocation["percentage"] = (
                    (allocation["usd_value"] / total_value_usd * 100)
                    if total_value_usd > 0
                    else 0.0
                )

            # Sort by USD value (descending)
            asset_allocation.sort(key=lambda x: x["usd_value"], reverse=True)

            # Calculate daily P&L using 24hr price changes
            daily_pnl, daily_pnl_percent = await self._calculate_daily_pnl(
                balances, prices, total_value_usd
            )

            return {
                "total_value_usd": total_value_usd,
                "total_value_btc": total_value_btc,
                "daily_pnl": daily_pnl,
                "daily_pnl_percent": daily_pnl_percent,
                "asset_allocation": asset_allocation,
                "btc_price_usd": btc_price_usd,
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
            }

        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            raise

    async def _get_asset_price_changes(self) -> Dict[str, float]:
        """Get 24hr price changes for all assets with caching."""
        try:
            # Check if we have cached price changes (cache for 5 minutes to avoid rate limiting)
            now = datetime.now(timezone.utc)
            if (
                self.price_changes_last_update
                and self.price_changes_cache
                and (now - self.price_changes_last_update).total_seconds() < 300
            ):  # 5 minutes cache
                logger.debug(
                    f"Using cached price changes for {len(self.price_changes_cache)} assets"
                )
                return self.price_changes_cache

            service = binance_service.__class__()
            async with service:
                # Get 24hr ticker statistics for all symbols
                ticker_result = await service._make_request(
                    "/api/v3/ticker/24hr",
                    "",  # No API key needed for public endpoint
                    is_testnet=False,  # Use mainnet for market data
                )

                if not ticker_result["success"]:
                    logger.warning(
                        f"Failed to get 24hr ticker data for asset changes: {ticker_result['error']}"
                    )
                    # Return cached data if available, even if stale
                    if self.price_changes_cache:
                        logger.info(
                            f"Using stale cached price changes due to API failure"
                        )
                        return self.price_changes_cache
                    return {}

                # Create a map of asset to 24hr price change percentage
                price_changes = {}
                for ticker in ticker_result["data"]:
                    if ticker["symbol"].endswith("USDT"):
                        asset = ticker["symbol"].replace("USDT", "")
                        try:
                            price_change_percent = float(ticker["priceChangePercent"])
                            price_changes[asset] = price_change_percent
                        except (ValueError, KeyError):
                            continue

                # Add stable coins with 0% change
                price_changes["USDT"] = 0.0
                price_changes["USDC"] = 0.0
                price_changes["BUSD"] = 0.0

                # Update cache
                self.price_changes_cache = price_changes
                self.price_changes_last_update = now

                logger.debug(
                    f"Retrieved and cached price changes for {len(price_changes)} assets"
                )
                return price_changes

        except Exception as e:
            logger.error(f"Failed to get asset price changes: {e}")
            # Return cached data if available, even if stale
            if self.price_changes_cache:
                logger.info(f"Using stale cached price changes due to exception: {e}")
                return self.price_changes_cache
            return {}

    async def _calculate_daily_pnl(
        self,
        balances: List[Dict[str, Any]],
        current_prices: Dict[str, float],
        current_total_usd: float,
    ) -> Tuple[float, float]:
        """Calculate daily P&L using 24hr price change data."""
        try:
            # Get 24hr ticker data for price changes
            service = binance_service.__class__()
            async with service:
                ticker_result = await service._make_request(
                    "/api/v3/ticker/24hr",
                    "",  # No API key needed for public endpoint
                    is_testnet=False,  # Use mainnet for market data
                )

                if not ticker_result["success"]:
                    logger.warning(
                        f"Failed to get 24hr ticker data for P&L calculation: {ticker_result['error']}"
                    )
                    return 0.0, 0.0

                # Create a map of symbol to 24hr price change
                price_changes = {}
                for ticker in ticker_result["data"]:
                    if ticker["symbol"].endswith("USDT"):
                        asset = ticker["symbol"].replace("USDT", "")
                        try:
                            price_change_percent = float(ticker["priceChangePercent"])
                            price_changes[asset] = (
                                price_change_percent / 100.0
                            )  # Convert to decimal
                        except (ValueError, KeyError):
                            continue

                # Calculate what the portfolio value was 24 hours ago
                total_pnl_usd = 0.0
                for balance in balances:
                    asset = balance["asset"]
                    total_balance = balance["total"]
                    current_price = current_prices.get(asset, 0.0)

                    if current_price > 0:
                        # Calculate the price 24 hours ago
                        if asset in price_changes:
                            price_change_decimal = price_changes[asset]
                            # If current price increased by X%, then yesterday's price was current_price / (1 + X%)
                            yesterday_price = current_price / (1 + price_change_decimal)
                        else:
                            # If no price change data, assume no change
                            yesterday_price = current_price

                        # Calculate P&L for this asset
                        current_value = total_balance * current_price
                        yesterday_value = total_balance * yesterday_price
                        asset_pnl = current_value - yesterday_value
                        total_pnl_usd += asset_pnl

                # Calculate percentage change
                yesterday_total_usd = current_total_usd - total_pnl_usd
                daily_pnl_percent = (
                    (total_pnl_usd / yesterday_total_usd * 100)
                    if yesterday_total_usd > 0
                    else 0.0
                )

                logger.debug(
                    f"Daily P&L calculated: ${total_pnl_usd:.2f} ({daily_pnl_percent:.2f}%)"
                )
                return total_pnl_usd, daily_pnl_percent

        except Exception as e:
            logger.error(f"Failed to calculate daily P&L: {e}")
            return 0.0, 0.0

    def _is_cache_valid(self, cache_key: str, realtime: bool = False) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache or cache_key not in self.last_update:
            return False

        time_diff = datetime.now(timezone.utc) - self.last_update[cache_key]
        ttl = self.realtime_cache_ttl if realtime else self.cache_ttl
        return time_diff.total_seconds() < ttl

    def _is_rate_limited(self, user_id: int) -> bool:
        """Check if user is currently rate limited."""
        if user_id not in self.rate_limit_until:
            return False

        current_time = (
            datetime.now(timezone.utc).timestamp() * 1000
        )  # Convert to milliseconds
        return current_time < self.rate_limit_until[user_id]

    def _can_make_request(self, user_id: int) -> bool:
        """Check if user can make a request based on rate limiting."""
        current_time = datetime.now(timezone.utc)

        # Initialize tracking for new users
        if user_id not in self.request_count:
            self.request_count[user_id] = 0
            self.request_window_start[user_id] = current_time

        # Reset window if 1 minute has passed
        if (current_time - self.request_window_start[user_id]).total_seconds() >= 60:
            self.request_count[user_id] = 0
            self.request_window_start[user_id] = current_time

        # Allow max 10 requests per minute per user
        if self.request_count[user_id] >= 10:
            return False

        self.request_count[user_id] += 1
        return True

    def _handle_rate_limit_error(self, user_id: int, error_msg: str):
        """Handle rate limit error and extract ban duration."""
        try:
            # Extract ban timestamp from error message
            # Format: "banned until 1754077076190"
            import re

            match = re.search(r"banned until (\d+)", error_msg)
            if match:
                ban_until = int(match.group(1))
                self.rate_limit_until[user_id] = ban_until
                ban_time = datetime.fromtimestamp(ban_until / 1000, tz=timezone.utc)
                logger.warning(f"User {user_id} rate limited until {ban_time}")
            else:
                # Default 5 minute ban if we can't parse the timestamp
                ban_until = (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).timestamp() * 1000
                self.rate_limit_until[user_id] = ban_until
                logger.warning(f"User {user_id} rate limited for 5 minutes (default)")
        except Exception as e:
            logger.error(f"Failed to parse rate limit error: {e}")
            # Default 5 minute ban
            ban_until = (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).timestamp() * 1000
            self.rate_limit_until[user_id] = ban_until

    def _get_mock_portfolio_data(self) -> Dict[str, Any]:
        """Return mock portfolio data when rate limited."""
        return {
            "total_value_usd": 0.0,
            "total_value_btc": 0.0,
            "daily_pnl": 0.0,
            "daily_pnl_percent": 0.0,
            "asset_allocation": [],
            "btc_price_usd": 50000.0,  # Default BTC price
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "is_mock_data": True,
            "message": "Rate limited - showing cached/mock data",
        }

    async def get_recent_trades(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a user."""
        try:
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                return []

            service = binance_service.__class__()
            async with service:
                # Get account information to find symbols with balances
                account_result = await service._make_request(
                    "/api/v3/account",
                    credentials["api_key"],
                    credentials["secret_key"],
                    is_testnet=credentials["is_testnet"],
                    signed=True,
                )

                if not account_result["success"]:
                    logger.warning(
                        f"Failed to get account data for trades: {account_result['error']}"
                    )
                    return []

                # Get symbols with non-zero balances
                symbols = []
                for balance in account_result["data"]["balances"]:
                    if float(balance["free"]) > 0 or float(balance["locked"]) > 0:
                        asset = balance["asset"]
                        if asset != "USDT":  # Skip USDT base currency
                            symbols.append(f"{asset}USDT")

                # Get recent trades for each symbol (limit to top 5 symbols)
                all_trades = []
                for symbol in symbols[:5]:
                    try:
                        trades_result = await service._make_request(
                            f"/api/v3/myTrades?symbol={symbol}&limit={limit}",
                            credentials["api_key"],
                            credentials["secret_key"],
                            is_testnet=credentials["is_testnet"],
                            signed=True,
                        )

                        if trades_result["success"] and trades_result["data"]:
                            for trade in trades_result["data"]:
                                all_trades.append(
                                    {
                                        "id": trade["id"],
                                        "symbol": trade["symbol"],
                                        "side": "BUY" if trade["isBuyer"] else "SELL",
                                        "quantity": float(trade["qty"]),
                                        "price": float(trade["price"]),
                                        "total": float(trade["quoteQty"]),
                                        "timestamp": int(trade["time"]),
                                        "pnl": 0.0,  # Would need more complex calculation for real P&L
                                    }
                                )
                    except Exception as e:
                        logger.warning(f"Failed to get trades for {symbol}: {e}")
                        continue

                # Sort by timestamp (most recent first) and limit
                all_trades.sort(key=lambda x: x["timestamp"], reverse=True)
                return all_trades[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent trades for user {user_id}: {e}")
            return []

    async def get_top_performers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing assets from Binance 24hr ticker data."""
        try:
            service = binance_service.__class__()
            async with service:
                # Get 24hr ticker statistics for all symbols
                ticker_result = await service._make_request(
                    "/api/v3/ticker/24hr",
                    "",  # No API key needed for public endpoint
                    is_testnet=False,  # Use mainnet for market data
                )

                if not ticker_result["success"]:
                    logger.warning(
                        f"Failed to get 24hr ticker data: {ticker_result['error']}"
                    )
                    return []

                # Filter for USDT pairs and sort by price change percentage
                usdt_pairs = []
                for ticker in ticker_result["data"]:
                    if ticker["symbol"].endswith("USDT") and ticker["symbol"] != "USDT":
                        try:
                            change_percent = float(ticker["priceChangePercent"])
                            price = float(ticker["lastPrice"])
                            volume = float(ticker["volume"])

                            # Filter out low volume or very low price coins
                            if volume > 1000 and price > 0.001:
                                usdt_pairs.append(
                                    {
                                        "symbol": ticker["symbol"].replace("USDT", ""),
                                        "name": ticker["symbol"].replace(
                                            "USDT", ""
                                        ),  # Could be enhanced with coin names
                                        "price": price,
                                        "change_percent": change_percent,
                                    }
                                )
                        except (ValueError, KeyError):
                            continue

                # Sort by price change percentage (descending) and limit
                usdt_pairs.sort(key=lambda x: x["change_percent"], reverse=True)
                return usdt_pairs[:limit]

        except Exception as e:
            logger.error(f"Failed to get top performers: {e}")
            return []


# Global portfolio service instance
portfolio_service = PortfolioService()
