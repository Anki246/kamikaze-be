#!/usr/bin/env python3
"""
FluxTrader Trading Session Analyzer
Analyze trading session performance and generate detailed reports
"""

import sys
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shared.logging_config import setup_logging, get_log_files

class TradingSessionAnalyzer:
    """Analyze FluxTrader trading session performance"""
    
    def __init__(self):
        self.logger = setup_logging("trading_analyzer", log_type="system")
        
    def parse_session_log(self, log_file_path: str) -> Dict[str, Any]:
        """Parse a trading session log file"""
        session_data = {
            'session_id': '',
            'start_time': None,
            'end_time': None,
            'strategy_type': 'unknown',
            'signals_detected': 0,
            'trades_executed': 0,
            'ai_confirmations': 0,
            'ai_rejections': 0,
            'symbols_analyzed': [],
            'pump_signals': 0,
            'dump_signals': 0,
            'account_balance_start': 0.0,
            'account_balance_end': 0.0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with open(log_file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Extract session ID from filename
            filename = Path(log_file_path).name
            if 'pump_dump' in filename:
                session_data['strategy_type'] = 'pump_dump'
            elif 'live_trading' in filename:
                session_data['strategy_type'] = 'live_trading'
            
            # Parse session ID from filename
            session_id_match = re.search(r'(\d{8}_\d{6})', filename)
            if session_id_match:
                session_data['session_id'] = session_id_match.group(1)
            
            # Parse log content
            for line in lines:
                # Extract timestamps
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                    if not session_data['start_time']:
                        session_data['start_time'] = timestamp
                    session_data['end_time'] = timestamp
                
                # Extract signals and trades
                if 'SIGNAL DETECTED' in line:
                    session_data['signals_detected'] += 1
                    if 'PUMP' in line:
                        session_data['pump_signals'] += 1
                    elif 'DUMP' in line:
                        session_data['dump_signals'] += 1
                
                if 'TRADE EXECUTED' in line or 'Trade executed' in line:
                    session_data['trades_executed'] += 1
                
                # Extract AI decisions
                if 'AI CONFIDENCE' in line or 'AI confirms' in line:
                    session_data['ai_confirmations'] += 1
                elif 'AI rejects' in line or 'AI REJECTION' in line:
                    session_data['ai_rejections'] += 1
                
                # Extract account balance
                balance_match = re.search(r'Account Balance.*?\$([0-9,.]+)', line)
                if balance_match:
                    balance = float(balance_match.group(1).replace(',', ''))
                    if session_data['account_balance_start'] == 0.0:
                        session_data['account_balance_start'] = balance
                    session_data['account_balance_end'] = balance
                
                # Extract symbols
                symbol_match = re.search(r'(BTC|ETH|BNB|ADA|XRP|SOL|DOT|DOGE|AVAX|LINK)USDT', line)
                if symbol_match:
                    symbol = symbol_match.group(0)
                    if symbol not in session_data['symbols_analyzed']:
                        session_data['symbols_analyzed'].append(symbol)
                
                # Extract errors and warnings
                if 'ERROR' in line:
                    session_data['errors'].append(line.strip())
                elif 'WARNING' in line:
                    session_data['warnings'].append(line.strip())
            
        except Exception as e:
            self.logger.error(f"Error parsing session log {log_file_path}: {e}")
        
        return session_data
    
    def analyze_recent_sessions(self, days: int = 7):
        """Analyze recent trading sessions"""
        print(f"📊 Analyzing Trading Sessions (Last {days} days)")
        print("=" * 70)
        
        log_files = get_log_files()
        session_logs = log_files['trading_sessions']
        
        # Filter logs from last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_logs = [
            log for log in session_logs 
            if datetime.fromtimestamp(log['modified']) > cutoff_date
        ]
        
        if not recent_logs:
            print(f"No trading session logs found in the last {days} days")
            return
        
        print(f"Found {len(recent_logs)} trading sessions to analyze\n")
        
        # Analyze each session
        sessions = []
        for log_file in recent_logs:
            session_data = self.parse_session_log(log_file['path'])
            sessions.append(session_data)
        
        # Generate summary statistics
        self.generate_session_summary(sessions, days)
        
        # Show individual session details
        print("\n📋 Individual Session Details:")
        print("-" * 50)
        
        for i, session in enumerate(sessions, 1):
            duration = "Unknown"
            if session['start_time'] and session['end_time']:
                duration_seconds = (session['end_time'] - session['start_time']).total_seconds()
                duration = f"{duration_seconds/60:.1f} minutes"
            
            balance_change = session['account_balance_end'] - session['account_balance_start']
            balance_change_str = f"{balance_change:+.2f}" if balance_change != 0 else "0.00"
            
            print(f"{i}. Session {session['session_id']} ({session['strategy_type']})")
            print(f"   Duration: {duration}")
            print(f"   Signals: {session['signals_detected']} | Trades: {session['trades_executed']}")
            print(f"   AI Decisions: {session['ai_confirmations']} confirms, {session['ai_rejections']} rejects")
            print(f"   Balance Change: ${balance_change_str}")
            print(f"   Symbols: {len(session['symbols_analyzed'])} analyzed")
            if session['errors']:
                print(f"   ❌ Errors: {len(session['errors'])}")
            print()
    
    def generate_session_summary(self, sessions: List[Dict], days: int):
        """Generate summary statistics for sessions"""
        if not sessions:
            return
        
        # Calculate totals
        total_sessions = len(sessions)
        total_signals = sum(s['signals_detected'] for s in sessions)
        total_trades = sum(s['trades_executed'] for s in sessions)
        total_ai_confirmations = sum(s['ai_confirmations'] for s in sessions)
        total_ai_rejections = sum(s['ai_rejections'] for s in sessions)
        total_pump_signals = sum(s['pump_signals'] for s in sessions)
        total_dump_signals = sum(s['dump_signals'] for s in sessions)
        
        # Calculate balance changes
        total_balance_change = 0
        sessions_with_balance = 0
        for session in sessions:
            if session['account_balance_start'] > 0 and session['account_balance_end'] > 0:
                total_balance_change += session['account_balance_end'] - session['account_balance_start']
                sessions_with_balance += 1
        
        # Strategy breakdown
        strategy_counts = defaultdict(int)
        for session in sessions:
            strategy_counts[session['strategy_type']] += 1
        
        # Symbol analysis
        all_symbols = set()
        for session in sessions:
            all_symbols.update(session['symbols_analyzed'])
        
        # Error analysis
        total_errors = sum(len(s['errors']) for s in sessions)
        total_warnings = sum(len(s['warnings']) for s in sessions)
        
        # Display summary
        print("📈 TRADING PERFORMANCE SUMMARY")
        print("-" * 50)
        print(f"Analysis Period: {days} days")
        print(f"Total Sessions: {total_sessions}")
        print(f"Total Signals Detected: {total_signals}")
        print(f"Total Trades Executed: {total_trades}")
        print(f"Signal-to-Trade Ratio: {(total_trades/total_signals*100):.1f}%" if total_signals > 0 else "N/A")
        
        print(f"\n🤖 AI DECISION ANALYSIS:")
        print(f"AI Confirmations: {total_ai_confirmations}")
        print(f"AI Rejections: {total_ai_rejections}")
        ai_total = total_ai_confirmations + total_ai_rejections
        if ai_total > 0:
            print(f"AI Confirmation Rate: {(total_ai_confirmations/ai_total*100):.1f}%")
        
        print(f"\n🎯 SIGNAL BREAKDOWN:")
        print(f"Pump Signals: {total_pump_signals}")
        print(f"Dump Signals: {total_dump_signals}")
        
        print(f"\n💰 FINANCIAL PERFORMANCE:")
        if sessions_with_balance > 0:
            avg_balance_change = total_balance_change / sessions_with_balance
            print(f"Total Balance Change: ${total_balance_change:+.2f}")
            print(f"Average per Session: ${avg_balance_change:+.2f}")
        else:
            print("Balance data not available")
        
        print(f"\n📊 STRATEGY BREAKDOWN:")
        for strategy, count in strategy_counts.items():
            percentage = (count / total_sessions) * 100
            print(f"{strategy.replace('_', ' ').title()}: {count} sessions ({percentage:.1f}%)")
        
        print(f"\n📈 MARKET COVERAGE:")
        print(f"Unique Symbols Analyzed: {len(all_symbols)}")
        if all_symbols:
            print(f"Symbols: {', '.join(sorted(all_symbols))}")
        
        print(f"\n🔍 SYSTEM HEALTH:")
        print(f"Total Errors: {total_errors}")
        print(f"Total Warnings: {total_warnings}")
        error_rate = (total_errors / total_sessions) if total_sessions > 0 else 0
        print(f"Average Errors per Session: {error_rate:.1f}")
    
    def generate_detailed_report(self, session_id: str):
        """Generate detailed report for a specific session"""
        print(f"📋 Detailed Report for Session: {session_id}")
        print("=" * 70)
        
        log_files = get_log_files()
        session_logs = log_files['trading_sessions']
        
        # Find the session log
        target_log = None
        for log_file in session_logs:
            if session_id in log_file['name']:
                target_log = log_file
                break
        
        if not target_log:
            print(f"❌ Session log not found for ID: {session_id}")
            return
        
        # Parse the session
        session_data = self.parse_session_log(target_log['path'])
        
        # Display detailed information
        print(f"Session ID: {session_data['session_id']}")
        print(f"Strategy: {session_data['strategy_type'].replace('_', ' ').title()}")
        print(f"Log File: {target_log['name']}")
        
        if session_data['start_time'] and session_data['end_time']:
            duration = session_data['end_time'] - session_data['start_time']
            print(f"Start Time: {session_data['start_time']}")
            print(f"End Time: {session_data['end_time']}")
            print(f"Duration: {duration.total_seconds()/60:.1f} minutes")
        
        print(f"\n📊 Performance Metrics:")
        print(f"Signals Detected: {session_data['signals_detected']}")
        print(f"  • Pump Signals: {session_data['pump_signals']}")
        print(f"  • Dump Signals: {session_data['dump_signals']}")
        print(f"Trades Executed: {session_data['trades_executed']}")
        print(f"AI Confirmations: {session_data['ai_confirmations']}")
        print(f"AI Rejections: {session_data['ai_rejections']}")
        
        if session_data['account_balance_start'] > 0:
            balance_change = session_data['account_balance_end'] - session_data['account_balance_start']
            print(f"\n💰 Financial Performance:")
            print(f"Starting Balance: ${session_data['account_balance_start']:.2f}")
            print(f"Ending Balance: ${session_data['account_balance_end']:.2f}")
            print(f"Balance Change: ${balance_change:+.2f}")
        
        if session_data['symbols_analyzed']:
            print(f"\n📈 Symbols Analyzed ({len(session_data['symbols_analyzed'])}):")
            for symbol in sorted(session_data['symbols_analyzed']):
                print(f"  • {symbol}")
        
        if session_data['errors']:
            print(f"\n❌ Errors ({len(session_data['errors'])}):")
            for error in session_data['errors'][-5:]:  # Show last 5 errors
                print(f"  • {error}")
        
        if session_data['warnings']:
            print(f"\n⚠️  Warnings ({len(session_data['warnings'])}):")
            for warning in session_data['warnings'][-5:]:  # Show last 5 warnings
                print(f"  • {warning}")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="FluxTrader Trading Session Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils/trading_analyzer.py --analyze --days 7        # Analyze last 7 days
  python utils/trading_analyzer.py --report --session-id 20250721_015230  # Detailed report
        """
    )
    
    parser.add_argument('--analyze', action='store_true', help='Analyze recent trading sessions')
    parser.add_argument('--report', action='store_true', help='Generate detailed session report')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--session-id', help='Session ID for detailed report')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    print("🚀 FluxTrader Trading Session Analyzer")
    print("=" * 70)
    
    analyzer = TradingSessionAnalyzer()
    
    if args.analyze:
        analyzer.analyze_recent_sessions(args.days)
    elif args.report:
        if not args.session_id:
            print("❌ Session ID required for detailed report. Use --session-id")
            return
        analyzer.generate_detailed_report(args.session_id)
    else:
        print("❌ No valid action specified. Use --help for usage information.")

if __name__ == "__main__":
    main()
