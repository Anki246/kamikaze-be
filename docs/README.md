# 🤖 FluxTrader

**Professional MCP-Integrated Cryptocurrency Trading Bot with AI-Powered Decision Making**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP Integration](https://img.shields.io/badge/MCP-Integrated-green.svg)](https://modelcontextprotocol.io/)
[![Real Trading](https://img.shields.io/badge/Trading-Live%20Money-red.svg)](https://binance.com/)
[![AI Powered](https://img.shields.io/badge/AI-Groq%20LLM-purple.svg)](https://groq.com/)

## 🎯 Overview

FluxTrader is a professional-grade cryptocurrency trading bot that combines:
- **AI-Powered Decision Making** via Groq LLM
- **MCP (Model Context Protocol)** architecture for modularity
- **Real-time Market Analysis** with ultra-aggressive technical indicators
- **Live Trading Execution** on Binance Futures
- **Professional Risk Management** with multi-level stop losses

## 🏗️ Modern Project Structure

```
FluxTrader/
├── app.py                          # 🚀 Main entry point
├── requirements.txt                # 📋 Dependencies
├── docs/                           # 📚 Documentation
│   ├── MCP_INTEGRATION_DOCUMENTATION.md
│   └── MCP_INTEGRATION_SUMMARY.md
├── streamlit/                      # 🌐 Web interface
│   └── streamlit_ui.py            # Streamlit dashboard
└── src/                            # 💻 Source code
    ├── agents/                     # 🤖 Trading agents
    │   └── fluxtrader/             # FluxTrader agent
    │       ├── agent.py            # Core trading logic
    │       └── config.py           # Configuration management
    ├── mcp_servers/                # 🔗 MCP server implementations
    │   ├── binance_server.py       # Binance API MCP server
    │   ├── technical_analysis_server.py # TA MCP server
    │   └── server_endpoint.py      # MCP endpoint server
    ├── mcp_client/                 # 📡 MCP client utilities
    │   └── client_utils.py         # MCP client implementation
    └── shared/                     # 🔧 Shared utilities
        ├── constants.py            # Common constants
        └── utils.py                # Utility functions
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd FluxTrader

# Create and activate conda environment
conda create -n mcp-env python=3.11
conda activate mcp-env

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
# Binance API Credentials (REQUIRED)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# Groq AI API Key (REQUIRED for AI features)
GROQ_API_KEY=your_groq_api_key

# Trading Configuration
TRADE_AMOUNT=50.0
LEVERAGE=10
TRAILING_TAKE_PROFIT=0.5
TRAILING_STOP_LOSS_1=0.3
TRAILING_STOP_LOSS_2=0.5
TRAILING_STOP_LOSS_3=0.8

# Trading Mode
REAL_TRADING=true  # Set to false for simulation
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Run the System

#### Option A: Complete Web Interface (Recommended)
```bash
# Start MCP servers and API
python app.py --api

# In another terminal, start the web dashboard
streamlit run frontend/streamlit_ui.py

# Then open your browser to:
# 🌐 Dashboard: http://localhost:8501
# 📚 API Docs: http://localhost:8000/docs

# Use the web interface to start/stop the trading bot
```

#### Option B: MCP Servers + API Only
```bash
# Start MCP servers and API (for web interface or custom integrations)
python app.py --api

# Then use the web interface or API calls to control the trading bot
```

#### Option C: MCP Servers Only
```bash
# Start only MCP servers (for direct MCP client connections)
python app.py

# Trading bot must be started via API calls or custom MCP clients
```

## 🏗️ **Architecture Overview**

The Enhanced Billa AI Trading Bot uses a **separated architecture**:

1. **🔗 MCP Servers** (`app.py`): Always running, provide trading infrastructure
2. **🌐 API Server** (`app.py --api`): Manages trading bot lifecycle via REST API
3. **🤖 Trading Bot**: Started/stopped **only** via web interface or API calls
4. **📊 Web Dashboard**: Controls the entire system through the API

**Key Benefits:**
- MCP servers run independently and remain stable
- Trading bot can be started/stopped without affecting infrastructure
- Web interface provides safe control with confirmations
- API allows custom integrations and programmatic control

## 🎛️ Features

### 🌐 Professional Web Interface
- **Real-time Dashboard** with live monitoring and controls
- **Start/Stop Trading Controls** with safety confirmations
- **Configuration Management** with live parameter updates
- **Performance Tracking** with P&L charts and metrics
- **Live Log Streaming** with filtering and search
- **Responsive Design** for desktop and mobile devices

### 🤖 AI-Powered Trading
- **Groq LLM Integration** for intelligent decision making
- **Real-time Market Analysis** with confidence scoring
- **Multi-factor Signal Validation** before trade execution
- **Adaptive Risk Assessment** based on market conditions

### 📊 Technical Analysis
- **Ultra-aggressive thresholds** (0.03% signal detection)
- **Multi-timeframe analysis** (1m, 5m, 15m, 1h, 4h, 1d)
- **Professional indicators** (RSI, MACD, Bollinger Bands, Moving Averages)
- **Support/Resistance levels** with Fibonacci retracements
- **Market correlation analysis** across multiple assets

### 🛡️ Risk Management
- **Multi-level trailing stop losses** (3 configurable levels)
- **Dynamic position sizing** based on account balance
- **Real-time balance validation** before each trade
- **Maximum drawdown protection**
- **Configurable leverage and trade amounts**

### 🔗 MCP Architecture
- **Modular design** with standardized interfaces
- **Enhanced error handling** and retry logic
- **Scalable server architecture** for future extensions
- **Professional logging** and monitoring

### 🚀 API Integration
- **FastAPI REST API** for programmatic control
- **WebSocket support** for real-time updates
- **Comprehensive endpoints** for all bot functions
- **OpenAPI documentation** at `/docs`

## 📈 Trading Pairs

The bot supports major cryptocurrency pairs:
- BTC/USDT, ETH/USDT, BNB/USDT
- SOL/USDT, ADA/USDT, XRP/USDT
- DOT/USDT, LINK/USDT, AVAX/USDT
- And more...

## ⚙️ Configuration Options

### Trading Parameters
- `TRADE_AMOUNT`: Base trade amount in USDT
- `LEVERAGE`: Trading leverage (1-125x)
- `SIGNAL_THRESHOLD`: Minimum signal strength (default: 0.03%)
- `MIN_CONFIDENCE`: Minimum AI confidence (default: 35%)

### Risk Management
- `TRAILING_STOP_LOSS_1/2/3`: Multi-level stop losses
- `TRAILING_TAKE_PROFIT`: Take profit percentage
- `MAX_POSITION_SIZE_PCT`: Maximum position size
- `MAX_DAILY_LOSS`: Daily loss limit

### Allocation Strategy
- `ALLOCATION_BTC`: Bitcoin allocation percentage
- `ALLOCATION_ETH`: Ethereum allocation percentage
- `ALLOCATION_ALT`: Altcoin allocation percentage

## 🔧 Development

### Project Structure Benefits
- **Separation of Concerns**: Clear module boundaries
- **Testability**: Easy to unit test individual components
- **Maintainability**: Organized codebase with logical grouping
- **Extensibility**: Easy to add new features and integrations
- **Professional Standards**: Follows Python best practices

### Code Quality
- **Type Hints**: Full type annotation support
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logging with multiple levels
- **Configuration**: Centralized configuration management
- **Documentation**: Comprehensive inline documentation

## 🚨 Important Warnings

⚠️ **REAL MONEY TRADING**: This bot trades with real money on Binance Futures. Use at your own risk.

⚠️ **API SECURITY**: Never commit API keys to version control. Always use environment variables.

⚠️ **TESTING**: Thoroughly test with small amounts before scaling up.

⚠️ **MONITORING**: Always monitor the bot's performance and market conditions.

## 📞 Support

For issues, questions, or contributions:
1. Check the documentation in the `docs/` directory
2. Review the configuration options
3. Ensure all environment variables are properly set
4. Check the logs for detailed error information

## 📄 License

This project is for educational and research purposes. Use responsibly and in accordance with your local regulations.

---

**🎉 Happy Trading with FluxTrader!** 🚀
