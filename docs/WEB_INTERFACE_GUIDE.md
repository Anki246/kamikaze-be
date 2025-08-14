# 🌐 FluxTrader - Web Interface Guide

## 🎯 Overview

FluxTrader now includes a comprehensive web interface that provides professional monitoring and control capabilities through a modern Streamlit dashboard. This guide covers everything you need to know about using the web interface.

## 🚀 Quick Start

### 1. Install Additional Dependencies

```bash
# Install web interface dependencies
pip install streamlit fastapi uvicorn plotly pandas requests websockets
```

### 2. Start the Web Interface

```bash
# Option A: Complete web interface (Recommended)
python start_web_interface.py

# Option B: Manual startup
# Terminal 1: Start API server
python app.py --api

# Terminal 2: Start Streamlit dashboard
streamlit run streamlit_ui.py
```

### 3. Access the Dashboard

- **🌐 Web Dashboard**: http://localhost:8501
- **📚 API Documentation**: http://localhost:8000/docs
- **🔗 API Health Check**: http://localhost:8000/health

## 🎮 Web Interface Features

### 📊 Control Panel Tab

**Agent Status Panel**
- Real-time bot status (Running/Stopped)
- Account balance and available funds
- Total trades executed and P&L
- MCP servers health status

**Start/Stop Controls**
- Prominent START/STOP trading buttons
- Safety confirmation for real money trading
- Real-time status updates

### 📈 Monitoring Tab

**Performance Dashboard**
- Recent trades table with details
- P&L charts and performance metrics
- Balance distribution pie chart
- Active positions overview

**Real-time Updates**
- Auto-refresh every 5 seconds
- Manual refresh button
- Live data streaming

### ⚙️ Configuration Tab

**Trading Parameters**
- Trade amount (USDT)
- Leverage settings (1-125x)
- Signal threshold percentage
- Take profit levels
- Multi-level stop losses (3 levels)
- Real trading mode toggle

**Safety Features**
- Parameter validation
- Real-time configuration updates
- Warning for real money trading

### 📝 Logs Tab

**Log Management**
- Real-time log streaming
- Log level filtering (INFO, WARNING, ERROR, DEBUG)
- Search functionality
- Color-coded log levels

**Log Sources**
- Bot operations
- AI decision making
- MCP server communications
- Trading execution

## 🔧 Technical Architecture

### API Server (FastAPI)
- **Port**: 8000
- **Endpoints**: RESTful API for all bot operations
- **WebSocket**: Real-time updates at `/ws`
- **Documentation**: Auto-generated at `/docs`

### Web Dashboard (Streamlit)
- **Port**: 8501
- **Framework**: Streamlit with custom CSS
- **Real-time**: Auto-refresh and WebSocket support
- **Responsive**: Works on desktop and mobile

### MCP Server Integration
- **Binance Server**: Port 8001
- **Technical Analysis Server**: Port 8002
- **Server Endpoint**: Port 8003
- **Health Monitoring**: Automatic restart on failure

## 🛡️ Safety Features

### Trading Confirmations
- Explicit confirmation required for starting real trading
- Clear warnings about real money usage
- Stop trading available at any time

### Error Handling
- Comprehensive error messages
- Graceful degradation on API failures
- Automatic reconnection attempts

### Configuration Validation
- Parameter range validation
- Real-time feedback on invalid inputs
- Safe defaults for all parameters

## 📱 Usage Scenarios

### Scenario 1: Monitor Existing Bot
1. Start the web interface
2. View real-time status and performance
3. Monitor logs and trading activity
4. Adjust parameters as needed

### Scenario 2: Start New Trading Session
1. Access the web dashboard
2. Review and adjust configuration
3. Confirm real trading mode
4. Click "START TRADING" with confirmation
5. Monitor performance in real-time

### Scenario 3: Emergency Stop
1. Access the dashboard from any device
2. Click "STOP TRADING" button
3. Confirm immediate shutdown
4. Review final performance metrics

## 🔍 Troubleshooting

### Common Issues

**API Server Not Starting**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process if needed
kill -9 <PID>

# Restart the API server
python app.py --api
```

**Streamlit Interface Not Loading**
```bash
# Check if port 8501 is in use
lsof -i :8501

# Restart Streamlit
streamlit run streamlit_ui.py --server.port=8501
```

**MCP Servers Not Connecting**
- Check environment variables (API keys)
- Verify network connectivity
- Review server logs for errors
- Restart MCP servers if needed

### Log Analysis

**Error Patterns to Watch**
- API connection failures
- Invalid trading parameters
- Insufficient account balance
- MCP server disconnections

**Performance Indicators**
- Response times < 2 seconds
- Successful trade execution rate
- AI confidence scores
- P&L trends

## 🎯 Best Practices

### Security
- Never share API keys or credentials
- Use environment variables for sensitive data
- Monitor access logs regularly
- Keep the interface on private networks

### Performance
- Monitor system resources
- Keep log files manageable
- Regular configuration backups
- Test with small amounts first

### Monitoring
- Check dashboard regularly
- Set up alerts for critical events
- Review performance metrics daily
- Maintain trading logs

## 🔄 API Endpoints

### Bot Control
- `POST /bot/start` - Start trading bot
- `POST /bot/stop` - Stop trading bot
- `GET /bot/status` - Get current status

### Configuration
- `GET /bot/config` - Get configuration
- `POST /bot/config` - Update configuration

### Data
- `GET /bot/trades` - Get recent trades
- `GET /bot/logs` - Get recent logs
- `GET /health` - Health check

### WebSocket
- `WS /ws` - Real-time updates

## 🎉 Advanced Features

### Custom Integrations
- Use the REST API for custom applications
- WebSocket for real-time data feeds
- Extend the Streamlit interface
- Add custom monitoring dashboards

### Automation
- Scheduled trading sessions
- Automated parameter adjustments
- Performance-based configuration
- Alert systems integration

---

**🚨 Important Reminders**

- Always test with small amounts first
- Monitor the bot actively during trading
- Keep API keys secure and private
- Review all configurations before starting
- Have a stop-loss strategy in place

**🎉 Happy Trading with Enhanced Billa AI!** 🚀
