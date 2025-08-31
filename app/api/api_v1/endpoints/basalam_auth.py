"""
Basalam Authentication Endpoints
Handles OAuth flow with Basalam API
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from app.db.database import get_db
from app.services.basalam_auth_service import BasalamAuthService
from app.models.user import User
from app.core.security import get_current_user
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/login")
async def basalam_login(
    current_user_id: str = Depends(get_current_user)
):
    """
    Initiate Basalam OAuth login process
    """
    basalam_service = BasalamAuthService()
    
    # Generate authorization URL with user ID as state
    auth_url = await basalam_service.get_authorization_url(state=current_user_id)
    
    return {
        "authorization_url": auth_url,
        "message": "Redirect user to this URL to authorize Basalam access"
    }

@router.get("/callback")
async def basalam_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Basalam OAuth callback
    """
    # Get authorization code and state from query parameters
    code = request.query_params.get("code")
    state = request.query_params.get("state")  # This should be the user ID
    error = request.query_params.get("error")
    
    if error:
        logger.error(f"Basalam OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?basalam_error={error}"
        )
    
    if not code or not state:
        logger.error("Missing authorization code or state in callback")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?basalam_error=missing_parameters"
        )
    
    basalam_service = BasalamAuthService()
    
    try:
        # Exchange authorization code for tokens
        tokens = await basalam_service.exchange_code_for_tokens(code)
        
        if not tokens:
            logger.error("Failed to exchange code for tokens")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?basalam_error=token_exchange_failed"
            )
        
        # Get user profile from Basalam
        user_profile = await basalam_service.get_user_profile(tokens["access_token"])
        
        # Store tokens for the user
        user_id = state
        success = await basalam_service.store_user_tokens(db, user_id, tokens)
        
        if success and user_profile:
            # Also store Basalam user ID
            from sqlalchemy import update
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(basalam_user_id=user_profile.get("id"))
            )
            await db.commit()
            
            logger.info(f"Successfully connected user {user_id} to Basalam")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?basalam_success=true"
            )
        else:
            logger.error("Failed to store tokens or get user profile")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?basalam_error=storage_failed"
            )
            
    except Exception as e:
        logger.error(f"Error in Basalam callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?basalam_error=callback_error"
        )

@router.get("/status")
async def basalam_status(
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check Basalam connection status for current user
    """
    basalam_service = BasalamAuthService()
    
    # Get user's stored tokens
    tokens = await basalam_service.get_user_tokens(db, current_user_id)
    
    if not tokens:
        return {
            "connected": False,
            "message": "No Basalam tokens found for this user"
        }
    
    # Check if token is valid
    valid_token = await basalam_service.ensure_valid_token(db, current_user_id)
    
    if valid_token:
        # Get user profile to confirm connection
        user_profile = await basalam_service.get_user_profile(valid_token)
        
        return {
            "connected": True,
            "user_profile": user_profile,
            "token_expires_at": tokens.get("expires_at")
        }
    else:
        return {
            "connected": False,
            "message": "Basalam token is expired or invalid"
        }

@router.delete("/disconnect")
async def disconnect_basalam(
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect user from Basalam by removing stored tokens
    """
    try:
        from sqlalchemy import update
        await db.execute(
            update(User)
            .where(User.id == current_user_id)
            .values(
                basalam_access_token=None,
                basalam_refresh_token=None,
                basalam_token_expires_at=None,
                basalam_user_id=None
            )
        )
        await db.commit()
        
        return {"message": "Successfully disconnected from Basalam"}
        
    except Exception as e:
        logger.error(f"Error disconnecting from Basalam: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disconnect from Basalam")

@router.get("/user-token")
async def get_user_basalam_token(
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current valid Basalam token for the user
    This endpoint is for internal use by other services
    """
    basalam_service = BasalamAuthService()
    
    # Ensure we have a valid token (refresh if needed)
    valid_token = await basalam_service.ensure_valid_token(db, current_user_id)
    
    if valid_token:
        return {
            "access_token": valid_token,
            "token_type": "Bearer"
        }
    else:
        raise HTTPException(
            status_code=401,
            detail="No valid Basalam token available. Please reconnect to Basalam."
        )