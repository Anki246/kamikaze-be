#!/usr/bin/env python3
"""
FluxTrader Configuration Manager
Manage and validate FluxTrader configuration settings
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from agents.fluxtrader.config import ConfigManager, config
from shared.logging_config import setup_logging

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class FluxTraderConfigManager:
    """Manage FluxTrader configuration with validation and updates"""

    def __init__(self):
        self.logger = setup_logging("config_manager", log_type="system")
        self.config_file = Path("config.json")

    def validate_configuration(self):
        """Validate current configuration"""
        print("🔍 Validating FluxTrader Configuration")
        print("=" * 60)

        issues = []
        warnings = []

        # Validate API configuration
        print("\n🔑 API Configuration:")
        if not config.api.binance_api_key:
            warnings.append("Binance API key not in environment variables (will retrieve from database)")
            print("ℹ️ Binance API Key: Not in environment (database retrieval available)")
        else:
            warnings.append("Binance API key found in environment variables (consider using database)")
            print("⚠️ Binance API Key: Configured in environment (consider database storage)")

        if not config.api.binance_secret_key:
            warnings.append("Binance secret key not in environment variables (will retrieve from database)")
            print("ℹ️ Binance Secret Key: Not in environment (database retrieval available)")
        else:
            warnings.append("Binance secret key found in environment variables (consider using database)")
            print("⚠️ Binance Secret Key: Configured in environment (consider database storage)")

        if not config.api.groq_api_key:
            warnings.append("Missing Groq API key - AI features will be disabled")
            print("⚠️  Groq API Key: Not configured (AI features disabled)")
        else:
            print("✅ Groq API Key: Configured")

        # Validate trading configuration
        print("\n💰 Trading Configuration:")
        if config.trading.trade_amount_usdt <= 0:
            issues.append("Invalid trade amount (must be > 0)")
            print(f"❌ Trade Amount: ${config.trading.trade_amount_usdt} (invalid)")
        else:
            print(f"✅ Trade Amount: ${config.trading.trade_amount_usdt}")

        if config.trading.leverage < 1 or config.trading.leverage > 125:
            issues.append("Invalid leverage (must be 1-125)")
            print(f"❌ Leverage: {config.trading.leverage}x (invalid)")
        else:
            print(f"✅ Leverage: {config.trading.leverage}x")

        # Validate thresholds
        print("\n🎯 Trading Thresholds:")
        if config.trading.pump_threshold <= 0:
            issues.append("Invalid pump threshold (must be > 0)")
            print(f"❌ Pump Threshold: {config.trading.pump_threshold}% (invalid)")
        else:
            print(f"✅ Pump Threshold: +{config.trading.pump_threshold}%")

        if config.trading.dump_threshold >= 0:
            issues.append("Invalid dump threshold (must be < 0)")
            print(f"❌ Dump Threshold: {config.trading.dump_threshold}% (invalid)")
        else:
            print(f"✅ Dump Threshold: {config.trading.dump_threshold}%")

        # Validate trading pairs
        print("\n📊 Trading Pairs:")
        if not config.app.trading_pairs:
            issues.append("No trading pairs configured")
            print("❌ Trading Pairs: None configured")
        else:
            print(f"✅ Trading Pairs: {len(config.app.trading_pairs)} pairs")
            for pair in config.app.trading_pairs[:5]:  # Show first 5
                print(f"   • {pair}")
            if len(config.app.trading_pairs) > 5:
                print(f"   ... and {len(config.app.trading_pairs) - 5} more")

        # Summary
        print("\n" + "=" * 60)
        print("📊 CONFIGURATION VALIDATION SUMMARY")
        print("=" * 60)

        if not issues and not warnings:
            print("✅ Configuration is valid and complete")
            return True
        else:
            if issues:
                print("❌ Critical Issues:")
                for issue in issues:
                    print(f"   • {issue}")

            if warnings:
                print("⚠️  Warnings:")
                for warning in warnings:
                    print(f"   • {warning}")

            return len(issues) == 0

    def show_configuration(self):
        """Display current configuration"""
        print("⚙️  FluxTrader Configuration")
        print("=" * 60)

        # API Settings
        print("\n🔑 API Settings:")
        print(
            f"   Binance API Key: {'✅ Set' if config.api.binance_api_key else '❌ Not set'}"
        )
        print(
            f"   Binance Secret: {'✅ Set' if config.api.binance_secret_key else '❌ Not set'}"
        )
        print(f"   Groq API Key: {'✅ Set' if config.api.groq_api_key else '❌ Not set'}")

        # Trading Settings
        print("\n💰 Trading Settings:")
        print(f"   Trade Amount: ${config.trading.trade_amount_usdt}")
        print(f"   Leverage: {config.trading.leverage}x")
        print(f"   Trading Mode: {config.trading_mode.mode}")
        print(f"   Enable Real Trades: {config.trading_mode.enable_real_trades}")

        # Trading Thresholds
        print("\n🎯 Trading Thresholds:")
        print(f"   Pump Threshold: +{config.trading.pump_threshold}%")
        print(f"   Dump Threshold: {config.trading.dump_threshold}%")
        print(f"   Min Confidence: {config.trading.min_confidence}%")
        print(f"   Signal Strength: {config.trading.signal_strength_threshold}")

        # AI Settings
        print("\n🤖 AI Settings:")
        print(f"   Model: {config.ai.model}")
        print(f"   Temperature: {config.ai.temperature}")
        print(f"   Max Tokens: {config.ai.max_tokens}")
        print(f"   Min Confidence Threshold: {config.ai.min_confidence_threshold}%")

        # Market Analysis
        print("\n📈 Market Analysis:")
        print(
            f"   Signal Strength Threshold: {config.market_analysis.signal_strength_threshold}"
        )
        print(f"   Momentum Threshold: {config.market_analysis.momentum_threshold}")
        print(f"   Volume Threshold: {config.market_analysis.volume_threshold:,}")

        # Trading Pairs
        print(f"\n📊 Trading Pairs ({len(config.app.trading_pairs)}):")
        for i, pair in enumerate(config.app.trading_pairs):
            print(f"   {i+1:2d}. {pair}")

        # Logging
        print(f"\n📝 Logging:")
        print(f"   Log Level: {config.logging.log_level}")
        print(f"   File Logging: {config.logging.enable_file_logging}")
        print(f"   Console Logging: {config.logging.enable_console_logging}")
        print(f"   Log Rotation: {config.logging.log_rotation}")

    def update_configuration(self, key_path: str, value: str):
        """Update a configuration value"""
        print(f"🔧 Updating Configuration: {key_path} = {value}")
        print("=" * 60)

        try:
            # Load current config
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    config_data = json.load(f)
            else:
                config_data = {}

            # Parse key path (e.g., "trading.max_trade_amount")
            keys = key_path.split(".")

            # Navigate to the correct section
            current = config_data
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]

            # Convert value to appropriate type
            final_key = keys[-1]
            old_value = current.get(final_key, "Not set")

            # Try to convert to appropriate type
            if value.lower() in ["true", "false"]:
                new_value = value.lower() == "true"
            elif value.replace(".", "").replace("-", "").isdigit():
                new_value = float(value) if "." in value else int(value)
            else:
                new_value = value

            # Update the value
            current[final_key] = new_value

            # Save updated config
            with open(self.config_file, "w") as f:
                json.dump(config_data, f, indent=2)

            print(f"✅ Updated {key_path}:")
            print(f"   Old value: {old_value}")
            print(f"   New value: {new_value}")
            print(f"   Config file updated: {self.config_file}")
            print("\n⚠️  Restart FluxTrader for changes to take effect")

        except Exception as e:
            print(f"❌ Failed to update configuration: {e}")
            return False

        return True

    def reset_configuration(self):
        """Reset configuration to defaults"""
        print("🔄 Resetting Configuration to Defaults")
        print("=" * 60)

        confirmation = input(
            "⚠️  This will reset ALL configuration to defaults. Continue? (type 'YES'): "
        )
        if confirmation != "YES":
            print("❌ Configuration reset cancelled")
            return False

        try:
            # Create new config manager with defaults
            default_config = ConfigManager()

            # Save default configuration
            default_config.save_to_json()

            print("✅ Configuration reset to defaults")
            print(f"   Config file: {self.config_file}")
            print("\n⚠️  You will need to reconfigure API keys and other settings")

        except Exception as e:
            print(f"❌ Failed to reset configuration: {e}")
            return False

        return True


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="FluxTrader Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils/config_manager.py --validate                    # Validate configuration
  python utils/config_manager.py --show                        # Show current config
  python utils/config_manager.py --set trading.max_trade_amount=100  # Update setting
  python utils/config_manager.py --reset                       # Reset to defaults
        """,
    )

    parser.add_argument(
        "--validate", action="store_true", help="Validate configuration"
    )
    parser.add_argument(
        "--show", action="store_true", help="Show current configuration"
    )
    parser.add_argument("--set", metavar="KEY=VALUE", help="Update configuration value")
    parser.add_argument(
        "--reset", action="store_true", help="Reset configuration to defaults"
    )

    args = parser.parse_args()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    print("🚀 FluxTrader Configuration Manager")
    print("=" * 70)

    manager = FluxTraderConfigManager()

    if args.validate:
        manager.validate_configuration()
    elif args.show:
        manager.show_configuration()
    elif args.set:
        if "=" not in args.set:
            print("❌ Invalid format. Use: --set key=value")
            return
        key, value = args.set.split("=", 1)
        manager.update_configuration(key, value)
    elif args.reset:
        manager.reset_configuration()
    else:
        print("❌ No valid action specified. Use --help for usage information.")


if __name__ == "__main__":
    main()
