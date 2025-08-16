"""
Mock Agent Manager for basic functionality
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentManager:
    """Mock agent manager for basic functionality."""

    def __init__(self):
        """Initialize mock agent manager."""
        self.agents = {}
        self.next_agent_id = 1
        logger.info("Mock AgentManager initialized")

    async def initialize(self):
        """Initialize the agent manager (async)."""
        logger.info("Mock AgentManager async initialization completed")
        return True

    def create_agent(self, user_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent.

        Args:
            user_id: User ID
            config: Agent configuration

        Returns:
            Agent creation result
        """
        try:
            agent_id = f"agent_{self.next_agent_id}"
            agent_data = {
                "id": agent_id,
                "user_id": user_id,
                "name": config.get("name", f"Agent {self.next_agent_id}"),
                "status": "created",
                "config": config,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "performance": {
                    "total_trades": 0,
                    "successful_trades": 0,
                    "total_pnl": 0.0,
                    "win_rate": 0.0,
                },
            }

            self.agents[agent_id] = agent_data
            self.next_agent_id += 1

            logger.info(f"Created agent {agent_id} for user {user_id}")
            return {"success": True, "agent": agent_data}

        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            return {"success": False, "error": str(e)}

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent data or None
        """
        return self.agents.get(agent_id)

    def get_user_agents(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all agents for a user.

        Args:
            user_id: User ID

        Returns:
            List of user's agents
        """
        return [agent for agent in self.agents.values() if agent["user_id"] == user_id]

    def update_agent(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent configuration.

        Args:
            agent_id: Agent ID
            config: New configuration

        Returns:
            Update result
        """
        try:
            if agent_id not in self.agents:
                return {"success": False, "error": "Agent not found"}

            self.agents[agent_id]["config"].update(config)
            self.agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()

            return {"success": True, "agent": self.agents[agent_id]}

        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            return {"success": False, "error": str(e)}

    def start_agent(self, agent_id: str) -> Dict[str, Any]:
        """Start an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Start result
        """
        try:
            if agent_id not in self.agents:
                return {"success": False, "error": "Agent not found"}

            self.agents[agent_id]["status"] = "running"
            self.agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()

            logger.info(f"Started agent {agent_id}")
            return {
                "success": True,
                "message": f"Agent {agent_id} started successfully",
            }

        except Exception as e:
            logger.error(f"Error starting agent {agent_id}: {e}")
            return {"success": False, "error": str(e)}

    def stop_agent(self, agent_id: str) -> Dict[str, Any]:
        """Stop an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Stop result
        """
        try:
            if agent_id not in self.agents:
                return {"success": False, "error": "Agent not found"}

            self.agents[agent_id]["status"] = "stopped"
            self.agents[agent_id]["updated_at"] = datetime.utcnow().isoformat()

            logger.info(f"Stopped agent {agent_id}")
            return {
                "success": True,
                "message": f"Agent {agent_id} stopped successfully",
            }

        except Exception as e:
            logger.error(f"Error stopping agent {agent_id}: {e}")
            return {"success": False, "error": str(e)}

    def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        """Delete an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Delete result
        """
        try:
            if agent_id not in self.agents:
                return {"success": False, "error": "Agent not found"}

            del self.agents[agent_id]

            logger.info(f"Deleted agent {agent_id}")
            return {
                "success": True,
                "message": f"Agent {agent_id} deleted successfully",
            }

        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_agent_performance(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent performance metrics.

        Args:
            agent_id: Agent ID

        Returns:
            Performance metrics or None
        """
        agent = self.agents.get(agent_id)
        return agent["performance"] if agent else None

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents.

        Returns:
            List of all agents
        """
        return list(self.agents.values())


# Global agent manager instance
agent_manager = AgentManager()
