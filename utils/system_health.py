#!/usr/bin/env python3
"""
FluxTrader System Health Monitor
Monitors system health, performance, and component status
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil

from agents.fluxtrader.config import config
from shared.logging_config import get_log_files, setup_logging

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class SystemHealthMonitor:
    """Monitor FluxTrader system health and performance"""

    def __init__(self):
        self.logger = setup_logging("system_health", log_type="system")

    def check_system_resources(self):
        """Check system resource usage"""
        print("💻 System Resources")
        print("-" * 40)

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_status = "✅" if cpu_percent < 80 else "⚠️" if cpu_percent < 95 else "❌"
        print(f"{cpu_status} CPU Usage: {cpu_percent:.1f}%")

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_status = (
            "✅" if memory_percent < 80 else "⚠️" if memory_percent < 95 else "❌"
        )
        print(
            f"{memory_status} Memory Usage: {memory_percent:.1f}% ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)"
        )

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        disk_status = "✅" if disk_percent < 80 else "⚠️" if disk_percent < 95 else "❌"
        print(
            f"{disk_status} Disk Usage: {disk_percent:.1f}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)"
        )

        # Network connections (with permission handling)
        try:
            connections = len(psutil.net_connections())
            conn_status = (
                "✅" if connections < 1000 else "⚠️" if connections < 2000 else "❌"
            )
            print(f"{conn_status} Network Connections: {connections}")
        except (psutil.AccessDenied, PermissionError):
            connections = 0
            conn_status = "⚠️"
            print(
                f"{conn_status} Network Connections: Permission denied (requires elevated privileges)"
            )

        return {
            "cpu": {"percent": cpu_percent, "status": cpu_status},
            "memory": {"percent": memory_percent, "status": memory_status},
            "disk": {"percent": disk_percent, "status": disk_status},
            "connections": {"count": connections, "status": conn_status},
        }

    def check_log_health(self):
        """Check log file health and recent errors"""
        print("\n📄 Log File Health")
        print("-" * 40)

        log_files = get_log_files()

        # Check system logs for recent errors
        error_count = 0
        warning_count = 0

        for log_file in log_files["system"]:
            try:
                with open(log_file["path"], "r") as f:
                    # Check last 100 lines for errors
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines

                    for line in recent_lines:
                        if "ERROR" in line:
                            error_count += 1
                        elif "WARNING" in line:
                            warning_count += 1
            except Exception as e:
                print(f"❌ Error reading {log_file['name']}: {e}")

        # Status based on error counts
        if error_count == 0:
            log_status = "✅"
        elif error_count < 5:
            log_status = "⚠️"
        else:
            log_status = "❌"

        print(f"{log_status} Recent Errors: {error_count}")
        print(f"⚠️  Recent Warnings: {warning_count}")

        # Check log file sizes
        total_log_size = 0
        for category in log_files.values():
            for log_file in category:
                total_log_size += log_file["size"]

        total_size_mb = total_log_size / (1024 * 1024)
        size_status = (
            "✅" if total_size_mb < 100 else "⚠️" if total_size_mb < 500 else "❌"
        )
        print(f"{size_status} Total Log Size: {total_size_mb:.1f} MB")

        return {
            "errors": error_count,
            "warnings": warning_count,
            "total_size_mb": total_size_mb,
            "status": log_status,
        }

    def check_configuration(self):
        """Check FluxTrader configuration health"""
        print("\n⚙️  Configuration Health")
        print("-" * 40)

        issues = []

        # Check API keys
        if not config.api.binance_api_key:
            print("ℹ️ Binance API key not in environment (database retrieval available)")
        else:
            print("⚠️ Binance API key found in environment (consider database storage)")
        if not config.api.binance_secret_key:
            print(
                "ℹ️ Binance secret key not in environment (database retrieval available)"
            )
        else:
            print(
                "⚠️ Binance secret key found in environment (consider database storage)"
            )
        if not config.api.groq_api_key:
            issues.append("Missing Groq API key (AI features disabled)")

        # Check trading configuration
        if config.trading.trade_amount_usdt <= 0:
            issues.append("Invalid trade amount")
        if config.trading.leverage < 1 or config.trading.leverage > 125:
            issues.append("Invalid leverage setting")

        # Check MCP configuration
        if not config.mcp.enabled:
            issues.append("MCP integration disabled")

        if not issues:
            print("✅ Configuration: All settings valid")
            config_status = "✅"
        else:
            print("❌ Configuration Issues:")
            for issue in issues:
                print(f"   • {issue}")
            config_status = "❌"

        return {"issues": issues, "status": config_status}

    async def check_mcp_connectivity(self):
        """Check MCP server connectivity"""
        print("\n🔗 MCP Connectivity")
        print("-" * 40)

        try:
            # Import and test MCP connection
            from agents.fluxtrader.agent import BinanceToolsInterface

            binance_tools = BinanceToolsInterface()

            # Test connection
            start_time = time.time()
            await binance_tools.connect_mcp_server()
            connection_time = time.time() - start_time

            if binance_tools.mcp_connected:
                print(f"✅ MCP Server: Connected ({connection_time:.2f}s)")

                # Test a simple API call
                try:
                    balance = await binance_tools.get_account_balance()
                    if balance and balance.get("success"):
                        print("✅ Binance API: Accessible")
                        api_status = "✅"
                    else:
                        print("❌ Binance API: Connection failed")
                        api_status = "❌"
                except Exception as e:
                    print(f"❌ Binance API: Error - {e}")
                    api_status = "❌"

                mcp_status = "✅"
            else:
                print("❌ MCP Server: Connection failed")
                print("❌ Binance API: Not accessible")
                mcp_status = "❌"
                api_status = "❌"

        except Exception as e:
            print(f"❌ MCP Connection Error: {e}")
            mcp_status = "❌"
            api_status = "❌"

        return {
            "mcp_status": mcp_status,
            "api_status": api_status,
            "connection_time": connection_time if "connection_time" in locals() else 0,
        }

    def generate_health_report(
        self, system_resources, log_health, config_health, mcp_health
    ):
        """Generate overall health report"""
        print("\n" + "=" * 60)
        print("📊 FLUXTRADER SYSTEM HEALTH REPORT")
        print("=" * 60)

        # Overall status
        all_statuses = [
            system_resources["cpu"]["status"],
            system_resources["memory"]["status"],
            system_resources["disk"]["status"],
            log_health["status"],
            config_health["status"],
            mcp_health["mcp_status"],
        ]

        if all(status == "✅" for status in all_statuses):
            overall_status = "✅ HEALTHY"
        elif any(status == "❌" for status in all_statuses):
            overall_status = "❌ CRITICAL"
        else:
            overall_status = "⚠️  WARNING"

        print(f"Overall Status: {overall_status}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Component summary
        print(f"\nComponent Status:")
        print(f"  System Resources: {system_resources['cpu']['status']}")
        print(f"  Log Health: {log_health['status']}")
        print(f"  Configuration: {config_health['status']}")
        print(f"  MCP Connectivity: {mcp_health['mcp_status']}")
        print(f"  Binance API: {mcp_health['api_status']}")

        # Recommendations
        recommendations = []

        if system_resources["cpu"]["percent"] > 80:
            recommendations.append(
                "High CPU usage - consider reducing trading frequency"
            )
        if system_resources["memory"]["percent"] > 80:
            recommendations.append("High memory usage - restart FluxTrader agent")
        if log_health["errors"] > 5:
            recommendations.append("Multiple recent errors - check log files")
        if config_health["issues"]:
            recommendations.append("Configuration issues detected - review settings")
        if mcp_health["mcp_status"] == "❌":
            recommendations.append("MCP connectivity issues - restart MCP server")

        if recommendations:
            print(f"\n🔧 Recommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
        else:
            print(f"\n🎉 No issues detected - system running optimally!")

        return overall_status


async def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="FluxTrader System Health Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils/system_health.py --check          # Quick health check
  python utils/system_health.py --monitor        # Continuous monitoring
  python utils/system_health.py --report         # Detailed health report
        """,
    )

    parser.add_argument(
        "--check", action="store_true", help="Perform quick health check"
    )
    parser.add_argument(
        "--monitor", action="store_true", help="Continuous monitoring mode"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate detailed health report"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)",
    )

    args = parser.parse_args()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    print("🚀 FluxTrader System Health Monitor")
    print("=" * 70)

    monitor = SystemHealthMonitor()

    if args.check or args.report:
        # Perform health checks
        system_resources = monitor.check_system_resources()
        log_health = monitor.check_log_health()
        config_health = monitor.check_configuration()
        mcp_health = await monitor.check_mcp_connectivity()

        if args.report:
            monitor.generate_health_report(
                system_resources, log_health, config_health, mcp_health
            )

    elif args.monitor:
        print(f"🔄 Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                print(f"\n📊 Health Check - {datetime.now().strftime('%H:%M:%S')}")
                system_resources = monitor.check_system_resources()

                # Quick status summary
                cpu_status = system_resources["cpu"]["status"]
                memory_status = system_resources["memory"]["status"]
                print(f"Status: CPU {cpu_status} | Memory {memory_status}")

                await asyncio.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped")


if __name__ == "__main__":
    asyncio.run(main())
