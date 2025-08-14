#!/usr/bin/env python3
"""
FluxTrader Log Management Utility
Provides easy management of the organized logs folder structure
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shared.logging_config import (
    get_log_files, 
    cleanup_old_logs,
    get_logs_directory
)

def list_logs():
    """List all log files organized by category"""
    print("📊 FluxTrader Log Files")
    print("=" * 60)
    
    log_files = get_log_files()
    
    # System logs
    print("\n📁 System Logs (logs/system/):")
    if log_files['system']:
        for log_file in log_files['system']:
            size_kb = log_file['size'] / 1024
            modified = datetime.fromtimestamp(log_file['modified']).strftime('%Y-%m-%d %H:%M')
            print(f"   📄 {log_file['name']} ({size_kb:.1f} KB) - {modified}")
    else:
        print("   (No system logs found)")
    
    # Trading session logs
    print("\n📁 Trading Session Logs (logs/trading_sessions/):")
    if log_files['trading_sessions']:
        for log_file in log_files['trading_sessions']:
            size_kb = log_file['size'] / 1024
            modified = datetime.fromtimestamp(log_file['modified']).strftime('%Y-%m-%d %H:%M')
            print(f"   📄 {log_file['name']} ({size_kb:.1f} KB) - {modified}")
    else:
        print("   (No trading session logs found)")
    
    # Archived logs
    print("\n📁 Archived Logs (logs/archived/):")
    if log_files['archived']:
        for log_file in log_files['archived']:
            size_kb = log_file['size'] / 1024
            modified = datetime.fromtimestamp(log_file['modified']).strftime('%Y-%m-%d %H:%M')
            print(f"   📄 {log_file['name']} ({size_kb:.1f} KB) - {modified}")
    else:
        print("   (No archived logs found)")
    
    # Summary
    total_files = (len(log_files['system']) + 
                   len(log_files['trading_sessions']) + 
                   len(log_files['archived']))
    
    total_size = 0
    for category in log_files.values():
        for log_file in category:
            total_size += log_file['size']
    
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"\n📊 Summary:")
    print(f"   Total files: {total_files}")
    print(f"   Total size: {total_size_mb:.2f} MB")

def show_recent_sessions(count=5):
    """Show recent trading sessions"""
    print(f"📈 Recent Trading Sessions (Last {count})")
    print("=" * 60)
    
    log_files = get_log_files()
    recent_sessions = log_files['trading_sessions'][:count]
    
    if not recent_sessions:
        print("No trading session logs found")
        return
    
    for i, log_file in enumerate(recent_sessions, 1):
        size_kb = log_file['size'] / 1024
        modified = datetime.fromtimestamp(log_file['modified']).strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract session type from filename
        name = log_file['name']
        if 'pump_dump' in name:
            session_type = "🚀 Pump/Dump"
        elif 'live_trading' in name:
            session_type = "💰 Live Trading"
        else:
            session_type = "📊 Trading"
        
        print(f"{i}. {session_type} Session")
        print(f"   📄 File: {name}")
        print(f"   📅 Date: {modified}")
        print(f"   📊 Size: {size_kb:.1f} KB")
        print(f"   📁 Path: {log_file['path']}")
        print()

def cleanup_logs(days=30, dry_run=False):
    """Clean up old log files"""
    print(f"🧹 Log Cleanup ({'DRY RUN' if dry_run else 'LIVE'})")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No files will be modified")
        print("Use --cleanup without --dry-run to actually clean up files")
        print()
    
    print(f"📅 Cleaning up logs older than {days} days")
    
    if not dry_run:
        cleanup_old_logs(days_to_keep=days, archive_old_sessions=True)
        print("✅ Log cleanup completed")
    else:
        print("✅ Dry run completed - use --cleanup to actually clean files")

def show_directory_structure():
    """Show the logs directory structure"""
    print("📁 Logs Directory Structure")
    print("=" * 60)
    
    logs_dir = get_logs_directory()
    print(f"📁 {logs_dir}")
    
    subdirs = ["system", "trading_sessions", "archived"]
    
    for subdir in subdirs:
        subdir_path = logs_dir / subdir
        if subdir_path.exists():
            log_files = list(subdir_path.glob("*.log"))
            total_size = sum(f.stat().st_size for f in log_files)
            size_mb = total_size / (1024 * 1024)
            
            print(f"├── 📁 {subdir}/")
            print(f"│   ├── Files: {len(log_files)}")
            print(f"│   └── Size: {size_mb:.2f} MB")
        else:
            print(f"├── 📁 {subdir}/ (not found)")
    
    # Show README
    readme_path = logs_dir / "README.md"
    if readme_path.exists():
        print(f"└── 📄 README.md ({readme_path.stat().st_size / 1024:.1f} KB)")
    else:
        print(f"└── 📄 README.md (not found)")

def tail_log(log_name, lines=20):
    """Show last N lines of a log file"""
    print(f"📄 Last {lines} lines of {log_name}")
    print("=" * 60)
    
    logs_dir = get_logs_directory()
    
    # Search for the log file in all subdirectories
    log_file = None
    for subdir in ["system", "trading_sessions", "archived"]:
        potential_path = logs_dir / subdir / log_name
        if potential_path.exists():
            log_file = potential_path
            break
    
    if not log_file:
        print(f"❌ Log file '{log_name}' not found")
        print("Available log files:")
        list_logs()
        return
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            for line in last_lines:
                print(line.rstrip())
                
        print(f"\n📊 Showing last {len(last_lines)} lines of {log_file}")
        
    except Exception as e:
        print(f"❌ Error reading log file: {e}")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="FluxTrader Log Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_logs.py --list                    # List all log files
  python manage_logs.py --recent 10               # Show 10 most recent sessions
  python manage_logs.py --structure               # Show directory structure
  python manage_logs.py --tail binance_tools.log  # Show last 20 lines of log
  python manage_logs.py --cleanup --dry-run       # Preview cleanup (safe)
  python manage_logs.py --cleanup                 # Actually clean up old logs
        """
    )
    
    parser.add_argument('--list', action='store_true', help='List all log files')
    parser.add_argument('--recent', type=int, metavar='N', help='Show N recent trading sessions')
    parser.add_argument('--structure', action='store_true', help='Show directory structure')
    parser.add_argument('--tail', metavar='LOGFILE', help='Show last lines of a log file')
    parser.add_argument('--lines', type=int, default=20, help='Number of lines for --tail (default: 20)')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old log files')
    parser.add_argument('--days', type=int, default=30, help='Days to keep for cleanup (default: 30)')
    parser.add_argument('--dry-run', action='store_true', help='Preview cleanup without making changes')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    print("🚀 FluxTrader Log Management Utility")
    print("=" * 70)
    
    if args.list:
        list_logs()
    elif args.recent is not None:
        show_recent_sessions(args.recent)
    elif args.structure:
        show_directory_structure()
    elif args.tail:
        tail_log(args.tail, args.lines)
    elif args.cleanup:
        cleanup_logs(args.days, args.dry_run)
    else:
        print("❌ No valid action specified. Use --help for usage information.")

if __name__ == "__main__":
    main()
