"""
User Status API Routes
Manages user connection status and environment switching (testnet/live)
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from ...infrastructure.credentials_database import credentials_db
from ...services.binance_connection_service import binance_service
from .auth_routes import get_current_user

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/user", tags=["User Status"])

# ============================================================================
# Pydantic Models
# ============================================================================

class UserStatusResponse(BaseModel):
    """Response model for user status."""
    success: bool
    message: str
    status: Optional[Dict[str, Any]] = None

class EnvironmentSwitchRequest(BaseModel):
    """Request model for environment switching."""
    environment: str = Field(..., description="Environment: 'testnet' or 'live'")

class ConnectionStatusResponse(BaseModel):
    """Response model for connection status."""
    success: bool
    message: str
    connection_status: Optional[Dict[str, Any]] = None

# ============================================================================
# User Status Routes
# ============================================================================

@router.get("/status", response_model=UserStatusResponse)
async def get_user_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get comprehensive user status including credentials and connection info."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(status_code=503, detail="Database service not available")
        
        user_id = current_user["id"]
        
        # Get Binance credentials status
        binance_creds = await credentials_db.get_user_binance_credentials(user_id)
        
        # Get testnet credentials status
        testnet_creds = await credentials_db.get_user_testnet_credentials(user_id)
        
        # Determine current environment preference
        # Priority: mainnet > testnet
        current_environment = "disconnected"
        if binance_creds['mainnet']:
            current_environment = "live"
        elif binance_creds['testnet'] or testnet_creds:
            current_environment = "testnet"
        
        # Build status response
        status = {
            "user_info": {
                "id": current_user["id"],
                "email": current_user["email"],
                "username": current_user["username"],
                "full_name": current_user.get("full_name")
            },
            "connection_status": {
                "current_environment": current_environment,
                "is_connected": current_environment != "disconnected"
            },
            "credentials": {
                "binance_mainnet": {
                    "configured": binance_creds['mainnet'] is not None,
                    "created_at": binance_creds['mainnet']['created_at'] if binance_creds['mainnet'] else None,
                    "updated_at": binance_creds['mainnet']['updated_at'] if binance_creds['mainnet'] else None
                },
                "binance_testnet": {
                    "configured": binance_creds['testnet'] is not None,
                    "created_at": binance_creds['testnet']['created_at'] if binance_creds['testnet'] else None,
                    "updated_at": binance_creds['testnet']['updated_at'] if binance_creds['testnet'] else None
                },
                "testnet_exchanges": [
                    {
                        "exchange": cred["exchange"],
                        "created_at": cred["created_at"],
                        "updated_at": cred["updated_at"]
                    }
                    for cred in testnet_creds
                ]
            },
            "available_environments": []
        }
        
        # Determine available environments
        if binance_creds['mainnet']:
            status["available_environments"].append("live")
        if binance_creds['testnet'] or testnet_creds:
            status["available_environments"].append("testnet")
        
        return UserStatusResponse(
            success=True,
            message="User status retrieved successfully",
            status=status
        )
        
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        return UserStatusResponse(
            success=False,
            message="An error occurred while retrieving user status"
        )

@router.get("/connection-status", response_model=ConnectionStatusResponse)
async def get_connection_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get detailed connection status for all configured exchanges."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(status_code=503, detail="Database service not available")
        
        user_id = current_user["id"]
        
        # Get all credentials
        binance_creds = await credentials_db.get_user_binance_credentials(user_id)
        testnet_creds = await credentials_db.get_user_testnet_credentials(user_id)
        
        connection_status = {
            "binance_mainnet": {"configured": False, "connected": False, "status": "not_configured"},
            "binance_testnet": {"configured": False, "connected": False, "status": "not_configured"},
            "overall_status": "disconnected",
            "active_environment": None,
            "last_tested": None
        }
        
        # Test Binance mainnet connection
        if binance_creds['mainnet']:
            connection_status["binance_mainnet"]["configured"] = True
            try:
                mainnet_creds = await credentials_db.get_binance_credentials(user_id, is_mainnet=True)
                if mainnet_creds:
                    async with binance_service as service:
                        test_result = await service.test_connection(
                            mainnet_creds['api_key'],
                            mainnet_creds['secret_key'],
                            is_testnet=False
                        )
                        connection_status["binance_mainnet"]["connected"] = test_result['success']
                        connection_status["binance_mainnet"]["status"] = "connected" if test_result['success'] else "error"
                        connection_status["binance_mainnet"]["error"] = test_result.get('error') if not test_result['success'] else None
                        
                        if test_result['success']:
                            connection_status["overall_status"] = "connected"
                            connection_status["active_environment"] = "live"
            except Exception as e:
                connection_status["binance_mainnet"]["status"] = "error"
                connection_status["binance_mainnet"]["error"] = str(e)
        
        # Test Binance testnet connection
        if binance_creds['testnet']:
            connection_status["binance_testnet"]["configured"] = True
            try:
                testnet_creds_binance = await credentials_db.get_binance_credentials(user_id, is_mainnet=False)
                if testnet_creds_binance:
                    async with binance_service as service:
                        test_result = await service.test_connection(
                            testnet_creds_binance['api_key'],
                            testnet_creds_binance['secret_key'],
                            is_testnet=True
                        )
                        connection_status["binance_testnet"]["connected"] = test_result['success']
                        connection_status["binance_testnet"]["status"] = "connected" if test_result['success'] else "error"
                        connection_status["binance_testnet"]["error"] = test_result.get('error') if not test_result['success'] else None
                        
                        if test_result['success'] and connection_status["overall_status"] == "disconnected":
                            connection_status["overall_status"] = "connected"
                            connection_status["active_environment"] = "testnet"
            except Exception as e:
                connection_status["binance_testnet"]["status"] = "error"
                connection_status["binance_testnet"]["error"] = str(e)
        
        # Check legacy testnet credentials
        for cred in testnet_creds:
            if cred["exchange"] == "binance" and not connection_status["binance_testnet"]["configured"]:
                connection_status["binance_testnet"]["configured"] = True
                try:
                    testnet_cred = await credentials_db.get_testnet_credentials(user_id, "binance")
                    if testnet_cred:
                        async with binance_service as service:
                            test_result = await service.test_connection(
                                testnet_cred['api_key'],
                                testnet_cred['secret_key'],
                                is_testnet=True
                            )
                            connection_status["binance_testnet"]["connected"] = test_result['success']
                            connection_status["binance_testnet"]["status"] = "connected" if test_result['success'] else "error"
                            connection_status["binance_testnet"]["error"] = test_result.get('error') if not test_result['success'] else None
                            
                            if test_result['success'] and connection_status["overall_status"] == "disconnected":
                                connection_status["overall_status"] = "connected"
                                connection_status["active_environment"] = "testnet"
                except Exception as e:
                    connection_status["binance_testnet"]["status"] = "error"
                    connection_status["binance_testnet"]["error"] = str(e)
        
        return ConnectionStatusResponse(
            success=True,
            message="Connection status retrieved successfully",
            connection_status=connection_status
        )
        
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        return ConnectionStatusResponse(
            success=False,
            message="An error occurred while checking connection status"
        )

@router.post("/switch-environment", response_model=UserStatusResponse)
async def switch_environment(
    request: EnvironmentSwitchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Switch user's active trading environment."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(status_code=503, detail="Database service not available")
        
        user_id = current_user["id"]
        
        # Validate environment
        if request.environment not in ["testnet", "live"]:
            return UserStatusResponse(
                success=False,
                message="Invalid environment. Must be 'testnet' or 'live'"
            )
        
        # Check if user has credentials for the requested environment
        binance_creds = await credentials_db.get_user_binance_credentials(user_id)
        testnet_creds = await credentials_db.get_user_testnet_credentials(user_id)
        
        if request.environment == "live":
            if not binance_creds['mainnet']:
                return UserStatusResponse(
                    success=False,
                    message="No mainnet credentials configured. Please add Binance mainnet credentials first."
                )
            
            # Test mainnet connection
            mainnet_creds = await credentials_db.get_binance_credentials(user_id, is_mainnet=True)
            async with binance_service as service:
                test_result = await service.test_connection(
                    mainnet_creds['api_key'],
                    mainnet_creds['secret_key'],
                    is_testnet=False
                )
                
                if not test_result['success']:
                    return UserStatusResponse(
                        success=False,
                        message=f"Cannot switch to live environment: {test_result['message']}"
                    )
        
        elif request.environment == "testnet":
            has_testnet = binance_creds['testnet'] or testnet_creds
            if not has_testnet:
                return UserStatusResponse(
                    success=False,
                    message="No testnet credentials configured. Please add testnet credentials first."
                )
            
            # Test testnet connection
            if binance_creds['testnet']:
                testnet_creds_binance = await credentials_db.get_binance_credentials(user_id, is_mainnet=False)
                async with binance_service as service:
                    test_result = await service.test_connection(
                        testnet_creds_binance['api_key'],
                        testnet_creds_binance['secret_key'],
                        is_testnet=True
                    )
                    
                    if not test_result['success']:
                        return UserStatusResponse(
                            success=False,
                            message=f"Cannot switch to testnet environment: {test_result['message']}"
                        )
            elif testnet_creds:
                # Check legacy testnet credentials
                testnet_cred = await credentials_db.get_testnet_credentials(user_id, "binance")
                if testnet_cred:
                    async with binance_service as service:
                        test_result = await service.test_connection(
                            testnet_cred['api_key'],
                            testnet_cred['secret_key'],
                            is_testnet=True
                        )
                        
                        if not test_result['success']:
                            return UserStatusResponse(
                                success=False,
                                message=f"Cannot switch to testnet environment: {test_result['message']}"
                            )
        
        # Environment switch successful
        return UserStatusResponse(
            success=True,
            message=f"Successfully switched to {request.environment} environment",
            status={
                "active_environment": request.environment,
                "switched_at": "now"  # In a real implementation, you might store this in the database
            }
        )
        
    except Exception as e:
        logger.error(f"Error switching environment: {e}")
        return UserStatusResponse(
            success=False,
            message="An error occurred while switching environment"
        )

@router.get("/available-environments")
async def get_available_environments(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get list of available environments for the user."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(status_code=503, detail="Database service not available")
        
        user_id = current_user["id"]
        
        # Get credentials
        binance_creds = await credentials_db.get_user_binance_credentials(user_id)
        testnet_creds = await credentials_db.get_user_testnet_credentials(user_id)
        
        environments = []
        
        # Check mainnet availability
        if binance_creds['mainnet']:
            environments.append({
                "environment": "live",
                "display_name": "Live Trading",
                "description": "Real Binance account with actual funds",
                "status": "available"
            })
        else:
            environments.append({
                "environment": "live",
                "display_name": "Live Trading",
                "description": "Real Binance account with actual funds",
                "status": "not_configured"
            })
        
        # Check testnet availability
        has_testnet = binance_creds['testnet'] or testnet_creds
        if has_testnet:
            environments.append({
                "environment": "testnet",
                "display_name": "Testnet Trading",
                "description": "Binance testnet for safe testing",
                "status": "available"
            })
        else:
            environments.append({
                "environment": "testnet",
                "display_name": "Testnet Trading",
                "description": "Binance testnet for safe testing",
                "status": "not_configured"
            })
        
        return {
            "success": True,
            "message": "Available environments retrieved successfully",
            "environments": environments
        }
        
    except Exception as e:
        logger.error(f"Error getting available environments: {e}")
        return {
            "success": False,
            "message": "An error occurred while retrieving environments"
        }
