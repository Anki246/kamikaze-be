"""
Exchange Credentials API Routes
Provides REST API endpoints for managing exchange API credentials
"""

import logging
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ...infrastructure.credentials_database import credentials_db
from ...services.binance_connection_service import binance_service
from .auth_routes import get_current_user

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/credentials", tags=["Exchange Credentials"])

# ============================================================================
# Pydantic Models
# ============================================================================


class TestnetCredentialsRequest(BaseModel):
    """Request model for testnet credentials."""

    exchange: str = Field(..., description="Exchange name (e.g., 'binance')")
    api_key: str = Field(..., description="API key")
    secret_key: str = Field(..., description="Secret key")


class BinanceCredentialsRequest(BaseModel):
    """Request model for Binance credentials."""

    api_key: str = Field(..., description="Binance API key")
    secret_key: str = Field(..., description="Binance secret key")
    is_mainnet: bool = Field(
        default=True, description="True for mainnet, False for testnet"
    )


class ConnectionTestRequest(BaseModel):
    """Request model for connection testing."""

    api_key: str = Field(..., description="API key")
    secret_key: str = Field(..., description="Secret key")
    is_testnet: bool = Field(default=False, description="Test against testnet")


class CredentialsResponse(BaseModel):
    """Response model for credentials operations."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ConnectionTestResponse(BaseModel):
    """Response model for connection test."""

    success: bool
    message: str
    account_info: Optional[Dict[str, Any]] = None
    permissions: Optional[list] = None
    environment: Optional[str] = None
    error_code: Optional[Union[str, int]] = None


# ============================================================================
# Testnet Credentials Routes
# ============================================================================


@router.post("/testnet", response_model=CredentialsResponse)
async def save_testnet_credentials(
    request: TestnetCredentialsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save testnet credentials for the authenticated user."""
    try:
        # Ensure database connection
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]

        # Validate exchange name
        if request.exchange.lower() not in ["binance"]:
            return CredentialsResponse(
                success=False,
                message="Unsupported exchange. Currently only 'binance' is supported.",
            )

        # Test connection before saving
        async with binance_service as service:
            test_result = await service.test_connection(
                request.api_key, request.secret_key, is_testnet=True
            )

            if not test_result["success"]:
                return CredentialsResponse(
                    success=False,
                    message=f"Connection test failed: {test_result['message']}",
                    data={"error_code": test_result.get("error_code")},
                )

        # Save credentials
        success = await credentials_db.save_testnet_credentials(
            user_id, request.exchange.lower(), request.api_key, request.secret_key
        )

        if success:
            return CredentialsResponse(
                success=True,
                message=f"Testnet credentials saved successfully for {request.exchange}",
                data={
                    "exchange": request.exchange.lower(),
                    "environment": "testnet",
                    "account_info": test_result.get("account_info"),
                },
            )
        else:
            return CredentialsResponse(
                success=False, message="Failed to save testnet credentials"
            )

    except Exception as e:
        logger.error(f"Error saving testnet credentials: {e}")
        return CredentialsResponse(
            success=False, message="An error occurred while saving credentials"
        )


@router.get("/testnet", response_model=CredentialsResponse)
async def get_testnet_credentials(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get all testnet credentials for the authenticated user."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]
        credentials = await credentials_db.get_user_testnet_credentials(user_id)

        return CredentialsResponse(
            success=True,
            message="Testnet credentials retrieved successfully",
            data={"credentials": credentials},
        )

    except Exception as e:
        logger.error(f"Error getting testnet credentials: {e}")
        return CredentialsResponse(
            success=False, message="An error occurred while retrieving credentials"
        )


# ============================================================================
# Binance Credentials Routes
# ============================================================================


@router.post("/binance", response_model=CredentialsResponse)
async def save_binance_credentials(
    request: BinanceCredentialsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save Binance credentials for the authenticated user."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]

        # Test connection before saving
        async with binance_service as service:
            test_result = await service.test_connection(
                request.api_key, request.secret_key, is_testnet=not request.is_mainnet
            )

            if not test_result["success"]:
                return CredentialsResponse(
                    success=False,
                    message=f"Connection test failed: {test_result['message']}",
                    data={"error_code": test_result.get("error_code")},
                )

        # Save credentials
        success = await credentials_db.save_binance_credentials(
            user_id, request.api_key, request.secret_key, request.is_mainnet
        )

        if success:
            env_type = "mainnet" if request.is_mainnet else "testnet"
            return CredentialsResponse(
                success=True,
                message=f"Binance {env_type} credentials saved successfully",
                data={
                    "environment": env_type,
                    "is_mainnet": request.is_mainnet,
                    "account_info": test_result.get("account_info"),
                },
            )
        else:
            return CredentialsResponse(
                success=False, message="Failed to save Binance credentials"
            )

    except Exception as e:
        logger.error(f"Error saving Binance credentials: {e}")
        return CredentialsResponse(
            success=False, message="An error occurred while saving credentials"
        )


@router.get("/binance", response_model=CredentialsResponse)
async def get_binance_credentials(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get Binance credentials status for the authenticated user."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]
        credentials = await credentials_db.get_user_binance_credentials(user_id)

        # Return status without sensitive data - prioritize mainnet for trading
        has_mainnet = credentials["mainnet"] is not None
        has_testnet = credentials["testnet"] is not None

        status = {
            "mainnet": {
                "configured": has_mainnet,
                "created_at": (
                    credentials["mainnet"]["created_at"]
                    if credentials["mainnet"]
                    else None
                ),
                "updated_at": (
                    credentials["mainnet"]["updated_at"]
                    if credentials["mainnet"]
                    else None
                ),
            },
            "testnet": {
                "configured": has_testnet,
                "created_at": (
                    credentials["testnet"]["created_at"]
                    if credentials["testnet"]
                    else None
                ),
                "updated_at": (
                    credentials["testnet"]["updated_at"]
                    if credentials["testnet"]
                    else None
                ),
            },
        }

        # For agent service compatibility - return the preferred credentials type
        # Prioritize mainnet for real trading, fallback to testnet
        preferred_env = (
            "mainnet" if has_mainnet else ("testnet" if has_testnet else None)
        )

        return CredentialsResponse(
            success=True,
            message="Binance credentials status retrieved successfully",
            data={
                "status": status,
                "has_credentials": has_mainnet or has_testnet,
                "mainnet": has_mainnet,
                "testnet": has_testnet,
                "preferred_environment": preferred_env,
            },
        )

    except Exception as e:
        logger.error(f"Error getting Binance credentials: {e}")
        return CredentialsResponse(
            success=False, message="An error occurred while retrieving credentials"
        )


# ============================================================================
# Connection Testing Routes
# ============================================================================


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(
    request: ConnectionTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Test connection to exchange with provided credentials."""
    try:
        async with binance_service as service:
            result = await service.test_connection(
                request.api_key, request.secret_key, request.is_testnet
            )

            # Add detailed error information for debugging
            response = ConnectionTestResponse(
                success=result["success"],
                message=result["message"],
                account_info=result.get("account_info"),
                permissions=result.get("permissions"),
                environment=result.get("environment"),
                error_code=result.get("error_code"),
            )

            # Log detailed error information for debugging
            if not result["success"]:
                logger.error(f"❌ Connection test failed for user {current_user['id']}")
                logger.error(f"   Error: {result.get('error')}")
                logger.error(f"   Error Code: {result.get('error_code')}")
                logger.error(f"   Message: {result.get('message')}")
                logger.error(f"   Environment: {result.get('environment')}")
                logger.error(f"   Full result: {result}")
            else:
                logger.info(
                    f"✅ Connection test succeeded for user {current_user['id']}"
                )
                logger.info(f"   Environment: {result.get('environment')}")
                logger.info(
                    f"   Account info: {result.get('account_info', {}).get('accountType', 'N/A')}"
                )

            return response

    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return ConnectionTestResponse(
            success=False, message="Connection test failed", error_code="TEST_ERROR"
        )


@router.post("/validate/{credential_type}")
async def validate_saved_credentials(
    credential_type: str,
    is_mainnet: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Validate saved credentials by testing connection."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]

        # Get credentials based on type
        if credential_type == "binance":
            creds = await credentials_db.get_binance_credentials(user_id, is_mainnet)
            is_testnet = not is_mainnet
        elif credential_type == "testnet":
            creds = await credentials_db.get_testnet_credentials(user_id, "binance")
            is_testnet = True
        else:
            raise HTTPException(status_code=400, detail="Invalid credential type")

        if not creds:
            return CredentialsResponse(
                success=False, message=f"No {credential_type} credentials found"
            )

        # Test connection
        async with binance_service as service:
            result = await service.test_connection(
                creds["api_key"], creds["secret_key"], is_testnet
            )

            return CredentialsResponse(
                success=result["success"],
                message=result["message"],
                data={
                    "environment": result.get("environment"),
                    "account_info": result.get("account_info"),
                    "permissions": result.get("permissions"),
                    "error_code": result.get("error_code"),
                },
            )

    except Exception as e:
        logger.error(f"Credential validation error: {e}")
        return CredentialsResponse(
            success=False, message="Credential validation failed"
        )


# ============================================================================
# Credential Management Routes
# ============================================================================


@router.delete("/binance")
async def delete_binance_credentials(
    is_mainnet: Optional[bool] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete Binance credentials for the authenticated user."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]

        success = await credentials_db.delete_credentials(
            user_id, "binance", is_mainnet=is_mainnet
        )

        if success:
            env_desc = (
                "all"
                if is_mainnet is None
                else ("mainnet" if is_mainnet else "testnet")
            )
            return CredentialsResponse(
                success=True,
                message=f"Binance {env_desc} credentials deleted successfully",
            )
        else:
            return CredentialsResponse(
                success=False, message="Failed to delete credentials"
            )

    except Exception as e:
        logger.error(f"Error deleting Binance credentials: {e}")
        return CredentialsResponse(
            success=False, message="An error occurred while deleting credentials"
        )


@router.delete("/testnet/{exchange}")
async def delete_testnet_credentials(
    exchange: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete testnet credentials for the authenticated user."""
    try:
        if not await credentials_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        user_id = current_user["id"]

        success = await credentials_db.delete_credentials(
            user_id, "testnet", exchange=exchange.lower()
        )

        if success:
            return CredentialsResponse(
                success=True,
                message=f"Testnet credentials for {exchange} deleted successfully",
            )
        else:
            return CredentialsResponse(
                success=False, message="Failed to delete credentials"
            )

    except Exception as e:
        logger.error(f"Error deleting testnet credentials: {e}")
        return CredentialsResponse(
            success=False, message="An error occurred while deleting credentials"
        )
