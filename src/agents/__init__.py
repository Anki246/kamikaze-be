"""
Trading Agents Package
Contains all trading agent implementations and the agent registry system.
"""

from .base_agent import (AgentConfig, AgentMetadata, AgentMetrics, AgentStatus,
                         BaseAgent, StrategyType)

# Agent factory functions will be available through the registry
# Avoiding circular imports by not importing agent_registry here

__all__ = [
    "BaseAgent",
    "AgentStatus",
    "StrategyType",
    "AgentMetadata",
    "AgentMetrics",
    "AgentConfig",
]
