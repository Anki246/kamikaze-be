# FluxTrader - AI-Powered Cryptocurrency Trading System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0-green.svg)](https://gofastmcp.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**FluxTrader** is an advanced AI-powered cryptocurrency trading system that combines real-time market analysis, pump/dump detection, and intelligent decision-making through Groq LLM integration. Built with standards-compliant MCP (Model Context Protocol) architecture for seamless integration and professional-grade reliability.

## 🚀 Key Features

### 🤖 AI-Powered Trading
- **Groq LLM Integration**: Intelligent trade validation with confidence scoring
- **Real-time Analysis**: Ultra-aggressive pump/dump detection (0.03% thresholds)
- **Multi-factor Decision Making**: Technical indicators + AI confirmation
- **Risk Management**: Professional position sizing and leverage controls

### 🔗 Enhanced FastMCP Integration
- **Standards-Compliant MCP Protocol**: JSON-RPC 2.0 over stdio transport
- **Real-time Market Data**: Live price feeds from Binance API
- **9 Trading Tools**: Complete trading functionality via MCP
- **Automatic Reconnection**: Robust error handling and recovery

### 📊 Advanced Market Analysis
- **Technical Indicators**: TA-Lib integration for professional analysis
- **Signal Detection**: Pump/dump, momentum, and volatility signals
- **Multi-timeframe Analysis**: Comprehensive market coverage
- **10+ Trading Pairs**: Major cryptocurrencies monitored

### 🛡️ Professional Risk Management
- **Multi-level Stop Loss**: Trailing stops with 3-tier protection
- **Position Sizing**: Intelligent allocation strategies
- **Leverage Control**: Configurable 1x-125x leverage
- **Balance Protection**: Real-time account monitoring

## 📁 Project Structure

```
FluxTrader/
├── README.md                   # This file
├── app.py                      # Main application entry point
├── config.json                 # System configuration
├── requirements.txt            # Python dependencies
│
├── src/                        # Core source code
│   ├── agents/                 # Trading agents
│   │   └── fluxtrader/        # FluxTrader agent implementation
│   ├── core/                   # Core functionality
│   ├── mcp_servers/           # MCP server implementations
│   └── shared/                # Shared utilities and logging
│
├── utils/                      # System utilities
│   ├── README.md              # Utility documentation
│   ├── manage_logs.py         # Log management
│   ├── system_health.py       # System monitoring
│   ├── config_manager.py      # Configuration management
│   ├── trading_analyzer.py    # Trading performance analysis
│   └── test_runner.py         # Test execution
│
├── logs/                       # Organized log files
│   ├── system/                # System component logs
│   ├── trading_sessions/      # Trading session logs
│   └── archived/              # Archived logs
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── MCP_INTEGRATION_DOCUMENTATION.md
│   └── WEB_INTERFACE_GUIDE.md
│
├── react-frontend/            # React.js frontend
└── streamlit/                 # Streamlit interface
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ (for React frontend)
- Binance API credentials
- Groq API key (optional, for AI features)

### 1. Clone Repository
```bash
git clone https://github.com/your-username/fluxtrader.git
cd fluxtrader
```

### 2. Create Virtual Environment
```bash
python -m venv .venv311
source .venv311/bin/activate  # On Windows: .venv311\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Create a `.env` file in the root directory:
```env
# Binance API (Required)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# Groq AI (Optional - for AI features)
GROQ_API_KEY=your_groq_api_key

# Trading Configuration
TRADING_MODE=REAL
ENABLE_REAL_TRADES=true
MAX_TRADE_AMOUNT=50.0
LEVERAGE=10
```

### 5. Validate Configuration
```bash
python utils/config_manager.py --validate
```

## 🚀 Quick Start

### Option 1: Streamlit Interface (Recommended)
```bash
# Start the Streamlit trading interface
cd streamlit
streamlit run app.py
```
Access at: http://localhost:8501

### Option 2: FastAPI Backend + React Frontend
```bash
# Terminal 1: Start FastAPI backend
python app.py --api backend

# Terminal 2: Start React frontend
cd react-frontend
npm install
npm start
```
Access at: http://localhost:3000

### Option 3: Direct Trading Execution
```bash
# Start MCP server
python src/mcp_servers/binance_fastmcp_server.py

# Run FluxTrader agent directly
python src/agents/fluxtrader/agent.py
```

## 📊 Trading Strategies

### Pump/Dump Strategy
- **Ultra-Aggressive Thresholds**: ±0.03% detection
- **AI Validation**: 35% minimum confidence
- **High Leverage**: 10-20x for maximum opportunity
- **Real-time Execution**: Sub-second signal processing

### Live Trading Strategy
- **Conservative Approach**: Higher confidence thresholds
- **Risk Management**: Lower leverage and position sizing
- **Continuous Monitoring**: 24/7 market surveillance
- **Adaptive Algorithms**: Learning from market conditions

## 🔧 System Management

### Health Monitoring
```bash
# Check system health
python utils/system_health.py --check

# Continuous monitoring
python utils/system_health.py --monitor
```

### Log Management
```bash
# View recent logs
python utils/manage_logs.py --list

# Analyze trading sessions
python utils/trading_analyzer.py --analyze --days 7

# Clean up old logs
python utils/manage_logs.py --cleanup --dry-run
```

### Configuration Management
```bash
# Show current configuration
python utils/config_manager.py --show

# Update settings
python utils/config_manager.py --set trading.trade_amount_usdt=100

# Validate configuration
python utils/config_manager.py --validate
```

## 🧪 Testing

### Run All Tests
```bash
python utils/test_runner.py --all
```

### Component Testing
```bash
# Test FluxTrader agent
python utils/test_runner.py --component fluxtrader

# Test MCP connectivity
python utils/test_runner.py --component mcp

# Integration tests
python utils/test_runner.py --integration
```

## 📈 Performance Metrics

### Real Trading Results
- **Signal Detection**: Ultra-aggressive 0.03% thresholds
- **AI Confirmation Rate**: 65-85% depending on market conditions
- **Execution Speed**: <3 second signal-to-trade latency
- **Market Coverage**: 10+ major cryptocurrency pairs
- **Uptime**: 99.9% with automatic recovery

### System Specifications
- **Memory Usage**: ~100MB base, ~200MB during active trading
- **CPU Usage**: <5% idle, <20% during signal processing
- **Network**: Minimal bandwidth, WebSocket connections
- **Storage**: Organized log rotation, <1GB typical usage

## 🛡️ Security & Risk Management

### API Security
- **Environment Variables**: Secure credential storage
- **No Hardcoded Keys**: All sensitive data externalized
- **Permission Scoping**: Minimal required API permissions

### Trading Risk Controls
- **Position Limits**: Configurable maximum position sizes
- **Stop Loss Protection**: Multi-level trailing stops
- **Balance Monitoring**: Real-time account balance tracking
- **Emergency Shutdown**: Immediate position closure capability

### System Security
- **Input Validation**: All user inputs sanitized
- **Error Handling**: Graceful failure recovery
- **Audit Logging**: Complete trading activity logs
- **Access Controls**: Secure configuration management

## ☁️ AWS Deployment

FluxTrader includes comprehensive AWS integration with automated infrastructure provisioning and secure secret management.

### Quick AWS Setup
```bash
# 1. Deploy infrastructure (5-10 minutes)
chmod +x scripts/deploy-infrastructure.sh
./scripts/deploy-infrastructure.sh \
  --environment staging \
  --tool cloudformation \
  --key-pair your-ec2-key-pair \
  --password your-secure-password

# 2. Configure GitHub secrets and trigger deployment
# See Quick Start Guide for details
```

### AWS Features
- **🏗️ Infrastructure as Code**: CloudFormation and Terraform templates
- **🔐 Secrets Management**: AWS Secrets Manager integration
- **🚀 Auto-scaling**: EC2 instances with load balancing (production)
- **🗄️ Managed Database**: RDS PostgreSQL with automated backups
- **📊 Monitoring**: CloudWatch logs and metrics
- **🔒 Security**: IAM roles, security groups, encryption at rest

### AWS Documentation
- **[🚀 Quick Start Guide](docs/QUICK_START_AWS.md)** - Get running in 30 minutes
- **[📖 Complete AWS Guide](docs/AWS_DEPLOYMENT_GUIDE.md)** - Comprehensive deployment documentation
- **[🏗️ Infrastructure Setup](infrastructure/)** - CloudFormation and Terraform templates

## 📚 Documentation

- **[Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md)**: System design and components
- **[MCP Integration](docs/MCP_INTEGRATION_DOCUMENTATION.md)**: FastMCP implementation details
- **[Web Interface Guide](docs/WEB_INTERFACE_GUIDE.md)**: Frontend usage instructions
- **[Utility Documentation](utils/README.md)**: System management tools
- **[CI/CD Pipeline](docs/CI_CD_PIPELINE.md)**: Complete CI/CD documentation
- **[AWS Deployment](docs/AWS_DEPLOYMENT_GUIDE.md)**: AWS infrastructure and deployment
- **[Quick Start AWS](docs/QUICK_START_AWS.md)**: 30-minute AWS setup guide

## 🔄 Maintenance & Operations

### Daily Operations
```bash
# Morning routine - check system health
python utils/system_health.py --check

# Review overnight trading performance
python utils/trading_analyzer.py --analyze --days 1

# Check for any errors or warnings
python utils/manage_logs.py --tail fluxtrader_trading_bot.log --lines 50
```

### Weekly Maintenance
```bash
# Generate weekly performance report
python utils/trading_analyzer.py --analyze --days 7

# Clean up old logs
python utils/manage_logs.py --cleanup --days 30

# Validate system configuration
python utils/config_manager.py --validate

# Run comprehensive system tests
python utils/test_runner.py --all
```

### Troubleshooting

#### Common Issues & Solutions

**MCP Connection Failed**
```bash
# Check MCP server status
python utils/system_health.py --check

# Restart MCP server
python src/mcp_servers/binance_fastmcp_server.py
```

**High Memory Usage**
```bash
# Monitor system resources
python utils/system_health.py --monitor --interval 30

# Clean up old logs
python utils/manage_logs.py --cleanup
```

**Trading Signals Not Detected**
```bash
# Check configuration thresholds
python utils/config_manager.py --show

# Analyze recent market data
python utils/trading_analyzer.py --analyze --days 1
```

## 🌟 Advanced Features

### Custom Strategy Development
FluxTrader supports custom trading strategies through the plugin architecture:

```python
# Example custom strategy
class CustomPumpDumpStrategy(TradingStrategy):
    def analyze_signal(self, market_data):
        # Your custom logic here
        return signal_strength, confidence
```

### API Integration
FluxTrader provides RESTful API endpoints for external integration:

```bash
# Start API server
python app.py --api backend

# Available endpoints:
# GET /api/status - System status
# GET /api/balance - Account balance
# POST /api/trade - Execute trade
# GET /api/positions - Active positions
```

### WebSocket Real-time Data
Real-time market data streaming via WebSocket:

```javascript
// Connect to real-time data stream
const ws = new WebSocket('ws://localhost:8000/ws/market-data');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Market update:', data);
};
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add comprehensive tests for new features
- Update documentation for API changes
- Use type hints for all functions
- Maintain backward compatibility

### Code Quality Standards
- **Test Coverage**: Minimum 80% code coverage
- **Documentation**: All public APIs documented
- **Type Safety**: Full type hint coverage
- **Security**: No hardcoded credentials or secrets
- **Performance**: Efficient algorithms and memory usage

## ⚙️ Configuration Reference

### Environment Variables
```env
# Required - Binance API Credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# Optional - AI Features
GROQ_API_KEY=your_groq_api_key_here

# Trading Configuration
TRADING_MODE=REAL                    # REAL or SIMULATION
ENABLE_REAL_TRADES=true             # Enable actual trade execution
MAX_TRADE_AMOUNT=50.0               # Maximum trade amount in USDT
LEVERAGE=10                         # Trading leverage (1-125)

# Strategy Parameters
PUMP_THRESHOLD=0.03                 # Pump detection threshold (%)
DUMP_THRESHOLD=-0.03                # Dump detection threshold (%)
MIN_CONFIDENCE=35                   # Minimum AI confidence (%)
SIGNAL_STRENGTH_THRESHOLD=0.4       # Signal strength threshold

# System Configuration
LOG_LEVEL=INFO                      # Logging level
ENABLE_FILE_LOGGING=true            # Enable file logging
MAX_LOG_FILES=10                    # Maximum log files to keep
```

### Configuration File (config.json)
The system uses a comprehensive JSON configuration file. Key sections:

```json
{
  "trading": {
    "leverage": 20,
    "trade_amount_usdt": 4.0,
    "pump_threshold": 0.03,
    "dump_threshold": -0.03,
    "min_confidence": 35
  },
  "risk_management": {
    "trailing_stop_loss_1": 1.5,
    "trailing_stop_loss_2": 2.5,
    "trailing_stop_loss_3": 4.0
  },
  "ai": {
    "model": "llama3-8b-8192",
    "temperature": 0.1,
    "max_tokens": 400,
    "min_confidence_threshold": 35
  }
}
```

### Trading Pairs
Default monitored pairs (configurable):
- BTCUSDT, ETHUSDT, BNBUSDT
- ADAUSDT, XRPUSDT, SOLUSDT
- DOTUSDT, DOGEUSDT, AVAXUSDT, LINKUSDT

## 🎯 Roadmap

### Version 2.0 (Planned)
- [ ] Multi-exchange support (Coinbase, Kraken)
- [ ] Advanced portfolio management
- [ ] Machine learning model training
- [ ] Mobile app interface
- [ ] Social trading features

### Version 1.5 (In Development)
- [ ] Enhanced backtesting engine
- [ ] Custom indicator development
- [ ] Advanced risk management rules
- [ ] Performance analytics dashboard
- [ ] Automated strategy optimization

### Current Version 1.0 ✅
- [x] AI-powered pump/dump detection
- [x] FastMCP integration
- [x] Real-time trading execution
- [x] Comprehensive logging system
- [x] System health monitoring
- [x] Web interface (Streamlit + React)

## 📊 System Requirements

### Minimum Requirements
- **OS**: Windows 10, macOS 10.15, Ubuntu 18.04+
- **Python**: 3.11 or higher
- **RAM**: 2GB available memory
- **Storage**: 5GB free space
- **Network**: Stable internet connection (10+ Mbps)

### Recommended Requirements
- **OS**: Latest stable versions
- **Python**: 3.11+ with virtual environment
- **RAM**: 4GB+ available memory
- **Storage**: 10GB+ free space (for logs and data)
- **Network**: High-speed connection (50+ Mbps)
- **CPU**: Multi-core processor for optimal performance

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**IMPORTANT**: FluxTrader is designed for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose. The developers are not responsible for any financial losses incurred through the use of this software.

- **High Risk**: Cryptocurrency trading is extremely volatile
- **No Guarantees**: Past performance does not guarantee future results
- **Use at Your Own Risk**: All trading decisions are your responsibility
- **Test First**: Always test with small amounts before scaling up

## 🆘 Support

### Getting Help
- **Documentation**: Check the `docs/` folder for detailed guides
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join community discussions
- **Wiki**: Community-maintained knowledge base

### Common Issues
- **API Connection**: Verify API keys and network connectivity
- **Permission Errors**: Ensure proper file permissions for logs
- **Memory Issues**: Monitor system resources during trading
- **Configuration**: Use `utils/config_manager.py --validate`

---

**FluxTrader** - Professional AI-Powered Cryptocurrency Trading System  
Built with ❤️ for the crypto trading community

*Last Updated: 2025-07-21*
