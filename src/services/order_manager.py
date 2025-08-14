#!/usr/bin/env python3
"""
24/7 Order Management Service
Handles trade execution, order tracking, and risk management
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.event_bus import (
    event_bus, publish_order_event, EventType, BaseEvent, TradingSignalEvent
)
from shared.logging_config import setup_logging
from agents.fluxtrader.fastmcp_client import FluxTraderMCPClient


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass
class Order:
    """Order data structure."""
    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    price: float
    order_type: OrderType
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    filled_quantity: float = 0.0
    average_price: float = 0.0
    commission: float = 0.0
    signal_id: Optional[str] = None
    strategy: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    error_message: Optional[str] = None


class RiskManager:
    """Risk management for order execution."""
    
    def __init__(self):
        self.max_position_size = 100.0  # Max USDT per position
        self.max_daily_loss = 50.0      # Max daily loss in USDT
        self.max_open_orders = 10       # Max concurrent orders
        self.daily_loss = 0.0
        self.daily_reset_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def check_order_risk(self, order: Order, current_balance: float, open_orders: List[Order]) -> tuple[bool, str]:
        """Check if order passes risk management rules."""
        
        # Reset daily loss if new day
        current_time = datetime.utcnow()
        if current_time.date() > self.daily_reset_time.date():
            self.daily_loss = 0.0
            self.daily_reset_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check position size
        position_value = order.quantity * order.price
        if position_value > self.max_position_size:
            return False, f"Position size ${position_value:.2f} exceeds max ${self.max_position_size}"
        
        # Check daily loss limit
        if self.daily_loss >= self.max_daily_loss:
            return False, f"Daily loss limit ${self.max_daily_loss} reached"
        
        # Check max open orders
        if len(open_orders) >= self.max_open_orders:
            return False, f"Max open orders ({self.max_open_orders}) reached"
        
        # Check available balance
        if order.side == "BUY" and position_value > current_balance * 0.9:  # Use max 90% of balance
            return False, f"Insufficient balance for order (${position_value:.2f} > ${current_balance * 0.9:.2f})"
        
        return True, "Risk check passed"
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L tracking."""
        if pnl < 0:
            self.daily_loss += abs(pnl)


class OrderManager:
    """
    24/7 Order Management Service.
    
    Features:
    - Subscribes to trading signals
    - Executes orders via MCP client
    - Risk management
    - Order tracking and status updates
    - Stop loss and take profit management
    - Performance monitoring
    """
    
    def __init__(self):
        self.logger = setup_logging("order_manager")
        self.running = False
        
        # MCP client for order execution
        self.mcp_client = FluxTraderMCPClient()
        
        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.open_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        
        # Risk management
        self.risk_manager = RiskManager()
        
        # Performance tracking
        self.orders_executed = 0
        self.orders_filled = 0
        self.total_pnl = 0.0
        self.current_balance = 0.0
        
        # Configuration
        self.auto_execute = True
        self.enable_stop_loss = True
        self.enable_take_profit = True
        
    async def start(self):
        """Start the order management service."""
        try:
            self.logger.info("🚀 Starting 24/7 Order Manager...")
            
            # Connect to event bus
            if not await event_bus.connect():
                raise Exception("Failed to connect to event bus")
            
            # Initialize MCP client
            if not await self.mcp_client.connect():
                raise Exception("Failed to connect to MCP server")
            
            # Subscribe to trading signals
            await event_bus.subscribe(
                "trading:signals:*",
                self._handle_trading_signal
            )
            
            # Subscribe to market data for stop loss/take profit
            await event_bus.subscribe(
                "trading:market_data:*",
                self._handle_market_data
            )
            
            # Start event listening
            await event_bus.start_listening()
            
            self.running = True
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self._order_monitor()),
                asyncio.create_task(self._stop_loss_monitor()),
                asyncio.create_task(self._performance_monitor()),
                asyncio.create_task(self._balance_updater())
            ]
            
            self.logger.info("✅ Order Manager started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Order Manager: {e}")
            raise
    
    async def stop(self):
        """Stop the order management service."""
        self.logger.info("🛑 Stopping Order Manager...")
        self.running = False
        
        # Cancel all open orders
        for order in self.open_orders.copy():
            await self._cancel_order(order.order_id)
        
        # Disconnect from services
        await self.mcp_client.disconnect()
        await event_bus.stop_listening()
        await event_bus.disconnect()
        
        self.logger.info("✅ Order Manager stopped")
    
    async def _handle_trading_signal(self, event: BaseEvent):
        """Handle incoming trading signals."""
        try:
            if event.event_type == EventType.TRADING_SIGNAL:
                symbol = event.data.get("symbol")
                signal_type = event.data.get("signal_type")
                confidence = event.data.get("confidence", 0)
                strategy = event.data.get("strategy", "unknown")
                price = event.data.get("price", 0)
                
                if symbol and signal_type and confidence > 0.3:  # Minimum confidence threshold
                    await self._process_trading_signal(
                        symbol, signal_type, confidence, strategy, price, event.correlation_id
                    )
                    
        except Exception as e:
            self.logger.error(f"❌ Error handling trading signal: {e}")
    
    async def _process_trading_signal(self, symbol: str, signal_type: str, confidence: float, 
                                    strategy: str, price: float, signal_id: str):
        """Process a trading signal and create order."""
        try:
            if not self.auto_execute:
                self.logger.info(f"📋 Signal received but auto-execute disabled: {signal_type} {symbol}")
                return
            
            # Calculate order quantity based on confidence and risk
            base_amount = 10.0  # Base USDT amount
            confidence_multiplier = min(confidence * 2, 1.5)  # Max 1.5x multiplier
            order_amount = base_amount * confidence_multiplier
            
            quantity = order_amount / price if price > 0 else 0
            
            if quantity <= 0:
                self.logger.warning(f"❌ Invalid quantity calculated for {symbol}: {quantity}")
                return
            
            # Create order
            order = Order(
                order_id=str(uuid.uuid4()),
                symbol=symbol,
                side=signal_type,
                quantity=quantity,
                price=price,
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                signal_id=signal_id,
                strategy=strategy
            )
            
            # Risk management check
            risk_passed, risk_message = self.risk_manager.check_order_risk(
                order, self.current_balance, self.open_orders
            )
            
            if not risk_passed:
                self.logger.warning(f"❌ Order rejected by risk management: {risk_message}")
                order.status = OrderStatus.REJECTED
                order.error_message = risk_message
                await self._update_order_status(order)
                return
            
            # Execute order
            await self._execute_order(order)
            
        except Exception as e:
            self.logger.error(f"❌ Error processing trading signal: {e}")
    
    async def _execute_order(self, order: Order):
        """Execute an order via MCP client."""
        try:
            self.logger.info(f"📤 Executing order: {order.side} {order.quantity:.6f} {order.symbol} @ ${order.price:.4f}")
            
            # Store order
            self.orders[order.order_id] = order
            self.open_orders.append(order)
            
            # Update status
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.utcnow()
            await self._update_order_status(order)
            
            # Execute via MCP
            if order.side == "BUY":
                result = await self.mcp_client.execute_buy_order(
                    order.symbol, order.quantity, order.price
                )
            else:
                result = await self.mcp_client.execute_sell_order(
                    order.symbol, order.quantity, order.price
                )
            
            # Process result
            if result and result.get("success"):
                order.status = OrderStatus.FILLED
                order.filled_quantity = order.quantity
                order.average_price = result.get("price", order.price)
                order.commission = result.get("commission", 0)
                
                # Move to completed orders
                if order in self.open_orders:
                    self.open_orders.remove(order)
                self.completed_orders.append(order)
                
                self.orders_filled += 1
                
                self.logger.info(f"✅ Order filled: {order.order_id} - {order.side} {order.filled_quantity:.6f} {order.symbol}")
                
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = result.get("error", "Unknown error") if result else "No response from MCP"
                
                if order in self.open_orders:
                    self.open_orders.remove(order)
                
                self.logger.error(f"❌ Order rejected: {order.order_id} - {order.error_message}")
            
            order.updated_at = datetime.utcnow()
            await self._update_order_status(order)
            
            self.orders_executed += 1
            
        except Exception as e:
            self.logger.error(f"❌ Error executing order {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
            order.updated_at = datetime.utcnow()
            
            if order in self.open_orders:
                self.open_orders.remove(order)
            
            await self._update_order_status(order)
    
    async def _cancel_order(self, order_id: str):
        """Cancel an order."""
        try:
            if order_id not in self.orders:
                return False
            
            order = self.orders[order_id]
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                return False
            
            # Cancel via MCP (if supported)
            # For now, just update status
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            
            if order in self.open_orders:
                self.open_orders.remove(order)
            
            await self._update_order_status(order)
            
            self.logger.info(f"🚫 Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    async def _update_order_status(self, order: Order):
        """Update order status and publish event."""
        try:
            # Publish order event
            await publish_order_event(
                event_type=EventType.ORDER_FILLED if order.status == OrderStatus.FILLED else EventType.ORDER_CREATED,
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.average_price or order.price,
                status=order.status.value
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error updating order status: {e}")
    
    async def _handle_market_data(self, event: BaseEvent):
        """Handle market data for stop loss/take profit monitoring."""
        try:
            if event.event_type == EventType.MARKET_DATA_UPDATE:
                symbol = event.data.get("symbol")
                price = event.data.get("price")
                
                if symbol and price:
                    # Check stop loss/take profit for open positions
                    await self._check_stop_loss_take_profit(symbol, price)
                    
        except Exception as e:
            self.logger.error(f"❌ Error handling market data: {e}")
    
    async def _check_stop_loss_take_profit(self, symbol: str, current_price: float):
        """Check stop loss and take profit conditions."""
        try:
            # Find filled orders for this symbol that might need stop loss/take profit
            for order in self.completed_orders:
                if (order.symbol == symbol and 
                    order.status == OrderStatus.FILLED and
                    (order.stop_loss or order.take_profit)):
                    
                    should_close = False
                    close_reason = ""
                    
                    if order.side == "BUY":
                        # For buy orders, check if price dropped below stop loss or rose above take profit
                        if order.stop_loss and current_price <= order.stop_loss:
                            should_close = True
                            close_reason = f"Stop loss triggered: ${current_price:.4f} <= ${order.stop_loss:.4f}"
                        elif order.take_profit and current_price >= order.take_profit:
                            should_close = True
                            close_reason = f"Take profit triggered: ${current_price:.4f} >= ${order.take_profit:.4f}"
                    
                    else:  # SELL order
                        # For sell orders, check if price rose above stop loss or dropped below take profit
                        if order.stop_loss and current_price >= order.stop_loss:
                            should_close = True
                            close_reason = f"Stop loss triggered: ${current_price:.4f} >= ${order.stop_loss:.4f}"
                        elif order.take_profit and current_price <= order.take_profit:
                            should_close = True
                            close_reason = f"Take profit triggered: ${current_price:.4f} <= ${order.take_profit:.4f}"
                    
                    if should_close:
                        await self._create_closing_order(order, current_price, close_reason)
                        
        except Exception as e:
            self.logger.error(f"❌ Error checking stop loss/take profit: {e}")
    
    async def _create_closing_order(self, original_order: Order, current_price: float, reason: str):
        """Create a closing order for stop loss or take profit."""
        try:
            # Create opposite order
            closing_side = "SELL" if original_order.side == "BUY" else "BUY"
            
            closing_order = Order(
                order_id=str(uuid.uuid4()),
                symbol=original_order.symbol,
                side=closing_side,
                quantity=original_order.filled_quantity,
                price=current_price,
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                strategy=f"{original_order.strategy}_close"
            )
            
            self.logger.info(f"🎯 Creating closing order: {reason}")
            await self._execute_order(closing_order)
            
            # Calculate P&L
            if original_order.side == "BUY":
                pnl = (current_price - original_order.average_price) * original_order.filled_quantity
            else:
                pnl = (original_order.average_price - current_price) * original_order.filled_quantity
            
            self.total_pnl += pnl
            self.risk_manager.update_daily_pnl(pnl)
            
            self.logger.info(f"💰 Position closed: P&L = ${pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Error creating closing order: {e}")
    
    async def _order_monitor(self):
        """Monitor order status and handle timeouts."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.utcnow()
                
                # Check for expired orders (older than 5 minutes)
                for order in self.open_orders.copy():
                    if order.status == OrderStatus.SUBMITTED:
                        time_diff = current_time - order.created_at
                        if time_diff > timedelta(minutes=5):
                            order.status = OrderStatus.EXPIRED
                            order.updated_at = current_time
                            self.open_orders.remove(order)
                            await self._update_order_status(order)
                            
                            self.logger.warning(f"⏰ Order expired: {order.order_id}")
                            
            except Exception as e:
                self.logger.error(f"❌ Error in order monitor: {e}")
    
    async def _stop_loss_monitor(self):
        """Monitor stop loss conditions."""
        while self.running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # This is handled in _handle_market_data, but we could add additional logic here
                
            except Exception as e:
                self.logger.error(f"❌ Error in stop loss monitor: {e}")
    
    async def _balance_updater(self):
        """Update account balance periodically."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Get balance via MCP
                balance_result = await self.mcp_client.get_account_balance()
                if balance_result and balance_result.get("success"):
                    self.current_balance = balance_result.get("available_balance", 0)
                    
            except Exception as e:
                self.logger.error(f"❌ Error updating balance: {e}")
    
    async def _performance_monitor(self):
        """Monitor and report performance metrics."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Report every 5 minutes
                
                # Calculate performance metrics
                win_rate = 0
                if self.orders_filled > 0:
                    profitable_orders = sum(1 for order in self.completed_orders 
                                          if hasattr(order, 'pnl') and order.pnl > 0)
                    win_rate = profitable_orders / self.orders_filled
                
                # Publish performance event
                performance_event = BaseEvent(
                    event_type=EventType.HEALTH_CHECK,
                    timestamp=datetime.utcnow(),
                    source="order_manager",
                    data={
                        "service": "order_manager",
                        "orders_executed": self.orders_executed,
                        "orders_filled": self.orders_filled,
                        "open_orders": len(self.open_orders),
                        "total_pnl": self.total_pnl,
                        "current_balance": self.current_balance,
                        "win_rate": win_rate,
                        "daily_loss": self.risk_manager.daily_loss
                    }
                )
                await event_bus.publish("trading:system:performance", performance_event)
                
            except Exception as e:
                self.logger.error(f"❌ Error in performance monitor: {e}")


# Main function for running as standalone service
async def main():
    """Main function for running order manager."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = OrderManager()
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
