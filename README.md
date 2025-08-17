# Kamikaze Bot - AI-Powered Cryptocurrency Trading Backend

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0-green.svg)](https://gofastmcp.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Kamikaze Bot** is an advanced AI-powered cryptocurrency trading backend system that combines real-time market analysis, pump/dump detection, and intelligent decision-making through Groq LLM integration. The system features **FluxTrader** as its core trading engine, built with standards-compliant MCP (Model Context Protocol) architecture for seamless integration and professional-grade reliability.

## 🚀 Key Features

### 🤖 AI-Powered Trading Engine (FluxTrader)
- **Groq LLM Integration**: Intelligent trade validation with confidence scoring
- **Real-time Analysis**: Ultra-aggressive pump/dump detection (0.03% thresholds)
- **Multi-factor Decision Making**: Technical indicators + AI confirmation
- **Risk Management**: Professional position sizing and leverage controls
- **Database-Managed Credentials**: Secure Binance API credential storage and retrieval

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

### 🏗️ Backend Architecture
- **FastAPI Backend**: RESTful API with real-time WebSocket communication
- **Multi-Agent System**: Modular agent-based trading architecture
- **PostgreSQL Integration**: Robust data persistence and analytics
- **AWS Integration**: Secure credential management with AWS Secrets Manager

## 📁 Project Structure

```
kamikaze-be/
├── README.md                   # This file
├── app.py                      # Main application entry point
├── config.json                 # System configuration
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker containerization
│
├── src/                        # Core source code
│   ├── agents/                 # Trading agents
│   │   ├── base_agent.py      # Base agent interface
│   │   └── fluxtrader/        # FluxTrader trading engine
│   ├── api/                    # FastAPI backend
│   │   ├── main.py            # API entry point
│   │   └── routers/           # API route handlers
│   ├── core/                   # Core functionality
│   ├── infrastructure/         # Database and AWS integration
│   ├── mcp_servers/           # MCP server implementations
│   ├── services/              # Business logic services
│   └── shared/                # Shared utilities and logging
│
├── utils/                      # System utilities
│   ├── manage_logs.py         # Log management
│   ├── system_health.py       # System monitoring
│   ├── config_manager.py      # Configuration management
│   └── trading_analyzer.py    # Trading performance analysis
│
├── scripts/                    # Utility scripts
│   ├── health-check.sh        # System health check
│   └── init-db.sql           # Database initialization
│
├── tests/                      # Test files
│   ├── test_aws.py           # AWS Secrets Manager tests
│   └── README.md             # Test documentation
│
├── logs/                       # Organized log files
│   ├── system/                # System component logs
│   ├── trading_sessions/      # Trading session logs
│   └── archived/              # Archived logs
│
└── docs/                       # Documentation
    └── [Additional documentation files]
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11 or higher
- AWS account with Secrets Manager configured:
  - `kmkz-db-secrets`: Database credentials
  - `kmkz-app-secrets`: AWS credentials, Groq API key, encryption keys
- PostgreSQL database (local or RDS)

### 1. Clone Repository
```bash
git clone https://github.com/Anki246/kamikaze-be.git
cd kamikaze-be
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

### 4. Database Setup
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql                              # macOS

# Create database
sudo -u postgres createdb kamikaze
```

### 5. Configure AWS Secrets Manager
Set up the following secrets in AWS Secrets Manager:

**`kmkz-db-secrets`** (Database credentials):
```json
{
  "username": "postgres",
  "password": "your_password",
  "host": "your-db-host",
  "port": 5432,
  "dbInstanceIdentifier": "kamikaze"
}
```

**`kmkz-app-secrets`** (Application secrets):
```json
{
  "AWS_ACCESS_KEY_ID": "your_aws_access_key",
  "AWS_SECRET_ACCESS_KEY": "your_aws_secret_key",
  "AWS_REGION": "us-east-1",
  "GROQ_API_KEY": "your_groq_api_key",
  "CREDENTIALS_ENCRYPTION_KEY": "your_encryption_key"
}
```

### 6. Start Application
```bash
python app.py
```

## 🚀 Quick Start

### Local Development
```bash
python app.py
```
Access the API at: http://localhost:8000/docs

### Docker Deployment
```bash
# Build and run
docker build -t kamikaze-bot .
docker run -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  kamikaze-bot
```

## 🎯 Core Capabilities

### FluxTrader Trading Engine
The heart of Kamikaze Bot is the FluxTrader trading engine, which provides:

#### Pump/Dump Detection Strategy
- **Ultra-Aggressive Thresholds**: ±0.03% detection for rapid market movements
- **AI Validation**: 35% minimum confidence scoring via Groq LLM
- **High Leverage**: 10-20x leverage for maximum opportunity capture
- **Real-time Execution**: Sub-second signal processing and trade execution

#### Live Trading Strategy
- **Conservative Approach**: Higher confidence thresholds for sustained trading
- **Risk Management**: Lower leverage and intelligent position sizing
- **Continuous Monitoring**: 24/7 market surveillance across multiple pairs
- **Adaptive Algorithms**: Learning from market conditions and performance

### Multi-Agent Architecture
- **Agent Management**: Centralized control of multiple trading agents
- **Real-time Communication**: WebSocket-based updates and notifications
- **Status Monitoring**: Live agent health and performance tracking
- **Scalable Design**: Easy addition of new trading strategies and agents

### Credential Management
- **AWS Secrets Manager**: Centralized credential storage
- **Database Storage**: User-specific Binance credentials in PostgreSQL
- **Encrypted Storage**: All sensitive data encrypted at rest

## 📡 API Documentation

### REST API Endpoints
```bash
# System
GET /health                     # System health check
GET /api/info                   # API information

# Agent Management
GET /api/agents                 # List trading agents
POST /api/agents/{id}/start     # Start agent
POST /api/agents/{id}/stop      # Stop agent

# Trading
GET /api/trading/balance        # Account balance
GET /api/trading/positions      # Active positions
POST /api/trading/execute       # Execute trade

# Market Data
GET /api/market/prices          # Current prices
GET /api/market/signals         # Trading signals
```

### WebSocket Endpoints
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/trading-updates');
```



## 🧪 Testing

```bash
# Test AWS Secrets Manager integration
python tests/test_aws.py

# System health check
./scripts/health-check.sh
curl http://localhost:8000/health

# API testing
curl http://localhost:8000/api/info
curl http://localhost:8000/api/agents
```

### API Testing
```bash
# Test API endpoints
curl http://localhost:8000/api/info
curl http://localhost:8000/api/agents
curl http://localhost:8000/api/trading/balance
```



## 🛡️ Security & Risk Management

- **AWS Secrets Manager**: Centralized credential management
- **Encrypted Storage**: All sensitive data encrypted at rest
- **Multi-level Stop Loss**: 3-tier trailing stop protection
- **Position Limits**: Configurable maximum position sizes
- **JWT Authentication**: Secure API access control

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

## 📚 Architecture

### Core Components
- **FastAPI Backend**: REST API and WebSocket communication
- **FluxTrader Engine**: AI-powered trading with Groq LLM integration
- **Multi-Agent System**: Scalable agent management and monitoring
- **AWS Integration**: Secrets Manager for credential storage
- **MCP Protocol**: Standards-compliant Binance API integration
- **[CI/CD Pipeline](docs/CI_CD_PIPELINE.md)**: Complete CI/CD documentation
- **[AWS Deployment](docs/AWS_DEPLOYMENT_GUIDE.md)**: AWS infrastructure and deployment
- **[Quick Start AWS](docs/QUICK_START_AWS.md)**: 30-minute AWS setup guide





## ⚙️ Configuration

Configuration is managed through:
- **AWS Secrets Manager**: Database and application credentials
- **config.json**: Trading parameters and system settings



## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---