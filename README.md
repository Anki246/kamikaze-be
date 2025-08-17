# Kamikaze Bot - AI-Powered Cryptocurrency Trading Backend

A sophisticated multi-agent cryptocurrency trading system with AI-powered decision making, real-time market analysis, and automated trading execution.

## 🚀 Features

### Core Trading Capabilities
- **AI-Powered Signal Validation**: Uses Groq LLM (llama3-8b-8192) for intelligent trade signal analysis
- **Ultra-Aggressive Technical Analysis**: 0.03% pump/dump detection thresholds
- **Real-Time Trade Execution**: Live trading with configurable risk management
- **Multi-Level Risk Management**: Trailing stop-loss and take-profit levels
- **24/7 Automated Trading**: Continuous market monitoring and execution

### Advanced Architecture
- **Multi-Agent System**: Modular agent-based architecture for scalability
- **MCP Integration**: Model Context Protocol for enhanced modularity
- **Real-Time WebSocket Communication**: Live updates and notifications
- **RESTful API**: Comprehensive API for system management
- **Event-Driven Microservices**: Scalable service orchestration

### Supported Features
- **Multiple Trading Pairs**: BTC, ETH, BNB, ADA, XRP, SOL, DOT, DOGE, AVAX, LINK
- **Flexible Trading Modes**: Real trading and simulation modes
- **Advanced Risk Management**: Configurable leverage, position sizing, and stop-losses
- **Database Integration**: PostgreSQL for data persistence
- **Authentication & Security**: JWT-based authentication with encrypted credentials
- **Health Monitoring**: System health checks and performance monitoring

## 🏗️ Architecture

### System Components
```
├── FastAPI Backend (Port 8000)
├── Multi-Agent Trading System
├── MCP Server Integration
├── PostgreSQL Database
├── Real-Time WebSocket Manager
├── Market Data API
└── Risk Management Engine
```

### Key Services
- **Agent Manager**: Manages trading agent lifecycle
- **Market Data Service**: Real-time market data processing
- **Order Manager**: Trade execution and order management
- **Strategy Engine**: Trading strategy implementation
- **Health Monitor**: System monitoring and alerts

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis (optional, for caching)
- Binance API credentials
- Groq API key for AI features

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kamikaze-be
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file with:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=kamikaze
   DB_USER=postgres
   DB_PASSWORD=your_password

   # Trading API Keys
   BINANCE_API_KEY=your_binance_api_key
   BINANCE_SECRET_KEY=your_binance_secret_key

   # AI Configuration
   GROQ_API_KEY=your_groq_api_key

   # Security
   JWT_SECRET_KEY=your_jwt_secret_key
   ```

4. **Initialize the database**
   ```bash
   # Database setup will be handled automatically on first run
   ```

## 🚀 Usage

### Start the Backend System
```bash
python app.py
```

### Start with Custom Configuration
```bash
python app.py --port 8000 --host 0.0.0.0
```

### Start Individual Services
```bash
# Start service orchestrator
python src/services/service_orchestrator.py

# Start standalone trading agent
python src/agents/fluxtrader/agent.py
```

## 📊 API Endpoints

### Core Endpoints
- `GET /` - API documentation (redirects to /docs)
- `GET /docs` - Interactive API documentation
- `GET /health` - System health check

### Trading Endpoints
- `POST /api/agents/start` - Start trading agent
- `POST /api/agents/stop` - Stop trading agent
- `GET /api/agents/status` - Get agent status
- `GET /api/market/data` - Get market data
- `GET /api/trading/positions` - Get current positions

### Authentication
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `GET /api/auth/profile` - User profile

## ⚙️ Configuration

### Trading Configuration (`config.json`)
```json
{
  "trading": {
    "leverage": 20,
    "trade_amount_usdt": 4,
    "pump_threshold": 0.03,
    "dump_threshold": -0.03,
    "min_confidence": 35
  },
  "risk_management": {
    "trailing_stop_loss": {
      "level_1": 1.5,
      "level_2": 2.5,
      "level_3": 4.0
    }
  }
}
```

### Key Configuration Options
- **Trading Mode**: `REAL` or `SIMULATION`
- **Leverage**: 1-125x leverage (default: 20x)
- **Risk Levels**: Multi-level stop-loss and take-profit
- **AI Settings**: Model configuration and confidence thresholds

## 🔒 Security Features

- JWT-based authentication
- Encrypted credential storage
- API key management
- User context middleware
- CORS protection
- Request rate limiting

## 📈 Monitoring & Logging

- Comprehensive logging system
- Real-time performance metrics
- Trade execution tracking
- System health monitoring
- Error reporting and alerts

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_aws.py
```

## 🚨 Risk Disclaimer

**WARNING**: This system executes real cryptocurrency trades with real money. 
- Only use funds you can afford to lose
- Cryptocurrency trading involves significant risk
- Past performance does not guarantee future results
- Always test in simulation mode first

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Support

For support and questions, please contact the development team.

---

**Kamikaze Bot** - Powered by AI, Built for Performance
