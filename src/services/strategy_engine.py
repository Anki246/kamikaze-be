#!/usr/bin/env python3
"""
24/7 Strategy Engine Service
Subscribes to market data events and generates trading signals using AI analysis
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from dataclasses import dataclass

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.event_bus import (
    event_bus, publish_trading_signal, EventType, BaseEvent, 
    MarketDataEvent, TradingSignalEvent
)
from shared.logging_config import setup_logging
from agents.fluxtrader.groq_client import GroqClient


@dataclass
class TradingSignal:
    """Trading signal data structure."""
    symbol: str
    signal_type: str  # "BUY", "SELL", "HOLD"
    confidence: float
    strategy: str
    price: float
    timestamp: datetime
    reasoning: str
    risk_level: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None


class StrategyEngine:
    """
    24/7 Strategy Engine for generating trading signals.
    
    Features:
    - Subscribes to market data events
    - AI-powered signal generation
    - Multiple trading strategies
    - Risk assessment
    - Signal validation and filtering
    - Real-time signal publishing
    """
    
    def __init__(self):
        self.logger = setup_logging("strategy_engine")
        self.running = False
        
        # Market data storage
        self.market_data: Dict[str, List[Dict]] = {}
        self.latest_prices: Dict[str, float] = {}
        
        # AI client for analysis
        self.groq_client = GroqClient()
        
        # Strategy parameters
        self.strategies = {
            "pump_dump": {
                "enabled": True,
                "min_confidence": 0.35,
                "pump_threshold": 0.03,  # 3% price increase
                "dump_threshold": -0.03,  # 3% price decrease
                "volume_multiplier": 2.0,  # 2x average volume
                "timeframe": "5m"
            },
            "momentum": {
                "enabled": True,
                "min_confidence": 0.40,
                "momentum_threshold": 0.02,  # 2% momentum
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "timeframe": "15m"
            },
            "mean_reversion": {
                "enabled": True,
                "min_confidence": 0.45,
                "deviation_threshold": 2.0,  # 2 standard deviations
                "lookback_period": 20,
                "timeframe": "1h"
            }
        }
        
        # Signal tracking
        self.recent_signals: Dict[str, List[TradingSignal]] = {}
        self.signal_cooldown = 300  # 5 minutes between signals for same symbol
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_confirmed = 0
        
    async def start(self):
        """Start the strategy engine."""
        try:
            self.logger.info("🚀 Starting 24/7 Strategy Engine...")
            
            # Connect to event bus
            if not await event_bus.connect():
                raise Exception("Failed to connect to event bus")
            
            # Subscribe to market data events
            await event_bus.subscribe(
                "trading:market_data:*",
                self._handle_market_data
            )
            
            # Subscribe to price change events
            await event_bus.subscribe(
                "trading:market_data:*",
                self._handle_price_change
            )
            
            # Start event listening
            await event_bus.start_listening()
            
            self.running = True
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self._signal_generator()),
                asyncio.create_task(self._signal_validator()),
                asyncio.create_task(self._performance_monitor())
            ]
            
            self.logger.info("✅ Strategy Engine started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Strategy Engine: {e}")
            raise
    
    async def stop(self):
        """Stop the strategy engine."""
        self.logger.info("🛑 Stopping Strategy Engine...")
        self.running = False
        
        await event_bus.stop_listening()
        await event_bus.disconnect()
        
        self.logger.info("✅ Strategy Engine stopped")
    
    async def _handle_market_data(self, event: BaseEvent):
        """Handle incoming market data events."""
        try:
            if event.event_type == EventType.MARKET_DATA_UPDATE:
                symbol = event.data.get("symbol")
                price = event.data.get("price")
                volume = event.data.get("volume")
                change_24h = event.data.get("change_24h")
                
                if symbol and price:
                    # Store market data
                    if symbol not in self.market_data:
                        self.market_data[symbol] = []
                    
                    data_point = {
                        "price": price,
                        "volume": volume,
                        "change_24h": change_24h,
                        "timestamp": event.timestamp
                    }
                    
                    self.market_data[symbol].append(data_point)
                    self.latest_prices[symbol] = price
                    
                    # Keep only last 1000 data points
                    if len(self.market_data[symbol]) > 1000:
                        self.market_data[symbol] = self.market_data[symbol][-1000:]
                    
                    self.logger.debug(f"📊 Updated market data for {symbol}: ${price:.4f}")
                    
        except Exception as e:
            self.logger.error(f"❌ Error handling market data: {e}")
    
    async def _handle_price_change(self, event: BaseEvent):
        """Handle rapid price change events."""
        try:
            if event.event_type == EventType.PRICE_CHANGE:
                symbol = event.data.get("symbol")
                change_percent = event.data.get("change_percent", 0)
                
                # Trigger immediate analysis for significant changes
                if abs(change_percent) > 0.02:  # 2% change
                    await self._analyze_symbol_immediate(symbol, "price_spike")
                    
        except Exception as e:
            self.logger.error(f"❌ Error handling price change: {e}")
    
    async def _signal_generator(self):
        """Main signal generation loop."""
        while self.running:
            try:
                await asyncio.sleep(10)  # Generate signals every 10 seconds
                
                # Analyze all symbols with sufficient data
                for symbol, data in self.market_data.items():
                    if len(data) >= 20:  # Need at least 20 data points
                        await self._analyze_symbol(symbol)
                        
            except Exception as e:
                self.logger.error(f"❌ Error in signal generator: {e}")
    
    async def _analyze_symbol(self, symbol: str):
        """Analyze a symbol and generate trading signals."""
        try:
            if symbol not in self.market_data or len(self.market_data[symbol]) < 20:
                return
            
            data = self.market_data[symbol]
            latest = data[-1]
            
            # Check signal cooldown
            if await self._is_signal_on_cooldown(symbol):
                return
            
            # Run different strategies
            signals = []
            
            # Pump/Dump Detection Strategy
            if self.strategies["pump_dump"]["enabled"]:
                signal = await self._pump_dump_strategy(symbol, data)
                if signal:
                    signals.append(signal)
            
            # Momentum Strategy
            if self.strategies["momentum"]["enabled"]:
                signal = await self._momentum_strategy(symbol, data)
                if signal:
                    signals.append(signal)
            
            # Mean Reversion Strategy
            if self.strategies["mean_reversion"]["enabled"]:
                signal = await self._mean_reversion_strategy(symbol, data)
                if signal:
                    signals.append(signal)
            
            # Process and validate signals
            for signal in signals:
                if signal.confidence >= self.strategies[signal.strategy]["min_confidence"]:
                    await self._publish_signal(signal)
                    
        except Exception as e:
            self.logger.error(f"❌ Error analyzing {symbol}: {e}")
    
    async def _pump_dump_strategy(self, symbol: str, data: List[Dict]) -> Optional[TradingSignal]:
        """Pump and dump detection strategy."""
        try:
            if len(data) < 10:
                return None
            
            recent_data = data[-10:]  # Last 10 data points
            prices = [d["price"] for d in recent_data]
            volumes = [d["volume"] for d in recent_data]
            
            # Calculate price change
            price_change = (prices[-1] - prices[0]) / prices[0]
            
            # Calculate volume spike
            avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
            volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
            
            strategy_config = self.strategies["pump_dump"]
            
            # Detect pump
            if (price_change > strategy_config["pump_threshold"] and 
                volume_ratio > strategy_config["volume_multiplier"]):
                
                # Use AI to analyze the pump
                ai_analysis = await self._ai_analyze_pump_dump(symbol, data, "pump")
                
                if ai_analysis and ai_analysis.get("confidence", 0) > 0.3:
                    return TradingSignal(
                        symbol=symbol,
                        signal_type="SELL",  # Sell on pump (expecting dump)
                        confidence=ai_analysis.get("confidence", 0.35),
                        strategy="pump_dump",
                        price=prices[-1],
                        timestamp=datetime.utcnow(),
                        reasoning=f"Pump detected: {price_change:.2%} price increase with {volume_ratio:.1f}x volume",
                        risk_level="HIGH",
                        target_price=prices[-1] * 0.97,  # 3% profit target
                        stop_loss=prices[-1] * 1.02   # 2% stop loss
                    )
            
            # Detect dump
            elif (price_change < strategy_config["dump_threshold"] and 
                  volume_ratio > strategy_config["volume_multiplier"]):
                
                ai_analysis = await self._ai_analyze_pump_dump(symbol, data, "dump")
                
                if ai_analysis and ai_analysis.get("confidence", 0) > 0.3:
                    return TradingSignal(
                        symbol=symbol,
                        signal_type="BUY",  # Buy on dump (expecting recovery)
                        confidence=ai_analysis.get("confidence", 0.35),
                        strategy="pump_dump",
                        price=prices[-1],
                        timestamp=datetime.utcnow(),
                        reasoning=f"Dump detected: {price_change:.2%} price decrease with {volume_ratio:.1f}x volume",
                        risk_level="HIGH",
                        target_price=prices[-1] * 1.03,  # 3% profit target
                        stop_loss=prices[-1] * 0.98   # 2% stop loss
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error in pump/dump strategy for {symbol}: {e}")
            return None
    
    async def _momentum_strategy(self, symbol: str, data: List[Dict]) -> Optional[TradingSignal]:
        """Momentum-based trading strategy."""
        try:
            if len(data) < 20:
                return None
            
            prices = [d["price"] for d in data[-20:]]
            
            # Calculate RSI
            rsi = self._calculate_rsi(prices)
            
            # Calculate momentum
            momentum = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
            
            strategy_config = self.strategies["momentum"]
            
            # Buy signal (oversold + positive momentum)
            if (rsi < strategy_config["rsi_oversold"] and 
                momentum > strategy_config["momentum_threshold"]):
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    confidence=0.42,
                    strategy="momentum",
                    price=prices[-1],
                    timestamp=datetime.utcnow(),
                    reasoning=f"Oversold RSI ({rsi:.1f}) with positive momentum ({momentum:.2%})",
                    risk_level="MEDIUM",
                    target_price=prices[-1] * 1.025,  # 2.5% profit target
                    stop_loss=prices[-1] * 0.985   # 1.5% stop loss
                )
            
            # Sell signal (overbought + negative momentum)
            elif (rsi > strategy_config["rsi_overbought"] and 
                  momentum < -strategy_config["momentum_threshold"]):
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    confidence=0.42,
                    strategy="momentum",
                    price=prices[-1],
                    timestamp=datetime.utcnow(),
                    reasoning=f"Overbought RSI ({rsi:.1f}) with negative momentum ({momentum:.2%})",
                    risk_level="MEDIUM",
                    target_price=prices[-1] * 0.975,  # 2.5% profit target
                    stop_loss=prices[-1] * 1.015   # 1.5% stop loss
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error in momentum strategy for {symbol}: {e}")
            return None
    
    async def _mean_reversion_strategy(self, symbol: str, data: List[Dict]) -> Optional[TradingSignal]:
        """Mean reversion trading strategy."""
        try:
            if len(data) < 20:
                return None
            
            prices = [d["price"] for d in data[-20:]]
            
            # Calculate moving average and standard deviation
            mean_price = sum(prices) / len(prices)
            std_dev = np.std(prices)
            
            current_price = prices[-1]
            z_score = (current_price - mean_price) / std_dev if std_dev > 0 else 0
            
            strategy_config = self.strategies["mean_reversion"]
            
            # Buy signal (price significantly below mean)
            if z_score < -strategy_config["deviation_threshold"]:
                return TradingSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    confidence=0.47,
                    strategy="mean_reversion",
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    reasoning=f"Price {z_score:.1f} std devs below mean (${mean_price:.4f})",
                    risk_level="LOW",
                    target_price=mean_price,  # Target mean price
                    stop_loss=current_price * 0.98   # 2% stop loss
                )
            
            # Sell signal (price significantly above mean)
            elif z_score > strategy_config["deviation_threshold"]:
                return TradingSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    confidence=0.47,
                    strategy="mean_reversion",
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    reasoning=f"Price {z_score:.1f} std devs above mean (${mean_price:.4f})",
                    risk_level="LOW",
                    target_price=mean_price,  # Target mean price
                    stop_loss=current_price * 1.02   # 2% stop loss
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error in mean reversion strategy for {symbol}: {e}")
            return None
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return 50  # Neutral RSI
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def _ai_analyze_pump_dump(self, symbol: str, data: List[Dict], event_type: str) -> Optional[Dict]:
        """Use AI to analyze pump/dump patterns."""
        try:
            # Prepare data for AI analysis
            recent_data = data[-20:] if len(data) >= 20 else data
            
            prompt = f"""
            Analyze this {event_type} pattern for {symbol}:
            
            Recent price data: {[d['price'] for d in recent_data[-10:]]}
            Recent volumes: {[d['volume'] for d in recent_data[-10:]]}
            
            Is this a genuine {event_type} or market manipulation?
            Provide confidence score (0-1) and brief reasoning.
            
            Response format: {{"confidence": 0.XX, "reasoning": "brief explanation"}}
            """
            
            response = await self.groq_client.get_completion(prompt)
            
            if response:
                try:
                    # Parse AI response
                    import re
                    confidence_match = re.search(r'"confidence":\s*([0-9.]+)', response)
                    reasoning_match = re.search(r'"reasoning":\s*"([^"]+)"', response)
                    
                    if confidence_match:
                        confidence = float(confidence_match.group(1))
                        reasoning = reasoning_match.group(1) if reasoning_match else "AI analysis"
                        
                        return {
                            "confidence": confidence,
                            "reasoning": reasoning
                        }
                except:
                    pass
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error in AI analysis: {e}")
            return None
    
    async def _is_signal_on_cooldown(self, symbol: str) -> bool:
        """Check if symbol is on signal cooldown."""
        if symbol not in self.recent_signals:
            return False
        
        recent_signals = self.recent_signals[symbol]
        if not recent_signals:
            return False
        
        last_signal_time = recent_signals[-1].timestamp
        time_diff = (datetime.utcnow() - last_signal_time).total_seconds()
        
        return time_diff < self.signal_cooldown
    
    async def _publish_signal(self, signal: TradingSignal):
        """Publish a trading signal."""
        try:
            # Store signal
            if signal.symbol not in self.recent_signals:
                self.recent_signals[signal.symbol] = []
            
            self.recent_signals[signal.symbol].append(signal)
            
            # Keep only last 10 signals per symbol
            if len(self.recent_signals[signal.symbol]) > 10:
                self.recent_signals[signal.symbol] = self.recent_signals[signal.symbol][-10:]
            
            # Publish signal event
            await publish_trading_signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                strategy=signal.strategy,
                price=signal.price
            )
            
            self.signals_generated += 1
            
            self.logger.info(
                f"🎯 SIGNAL: {signal.signal_type} {signal.symbol} @ ${signal.price:.4f} "
                f"({signal.confidence:.1%} confidence, {signal.strategy} strategy)"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error publishing signal: {e}")
    
    async def _analyze_symbol_immediate(self, symbol: str, trigger: str):
        """Immediate analysis triggered by events."""
        try:
            self.logger.info(f"🔍 Immediate analysis for {symbol} (trigger: {trigger})")
            await self._analyze_symbol(symbol)
        except Exception as e:
            self.logger.error(f"❌ Error in immediate analysis: {e}")
    
    async def _signal_validator(self):
        """Validate and confirm signals."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Validate every minute
                
                # Here you could implement signal validation logic
                # For example, checking if signals are still valid after some time
                
            except Exception as e:
                self.logger.error(f"❌ Error in signal validator: {e}")
    
    async def _performance_monitor(self):
        """Monitor strategy performance."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Report every 5 minutes
                
                # Publish performance metrics
                performance_event = BaseEvent(
                    event_type=EventType.HEALTH_CHECK,
                    timestamp=datetime.utcnow(),
                    source="strategy_engine",
                    data={
                        "service": "strategy_engine",
                        "signals_generated": self.signals_generated,
                        "signals_confirmed": self.signals_confirmed,
                        "active_symbols": len(self.market_data),
                        "strategies_enabled": sum(1 for s in self.strategies.values() if s["enabled"])
                    }
                )
                await event_bus.publish("trading:system:performance", performance_event)
                
            except Exception as e:
                self.logger.error(f"❌ Error in performance monitor: {e}")


# Main function for running as standalone service
async def main():
    """Main function for running strategy engine."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    engine = StrategyEngine()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
