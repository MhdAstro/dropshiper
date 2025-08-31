"""
Basalam Authentication Service
Handles authentication with Basalam API including token management
"""

import httpx
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.config import settings
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class BasalamAuthService:
    def __init__(self):
        self.base_url = "https://api.basalam.com"
        self.client_id = settings.BASALAM_API_KEY
        self.client_secret = settings.BASALAM_API_SECRET
        
    async def get_authorization_url(self, state: str = None) -> str:
        """
        Generate authorization URL for OAuth flow
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/basalam/callback",
            "scope": "customer_wallet_read customer_wallet_write vendor_product_read vendor_product_write customer_order_read",
            "state": state or "random_state"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}/oauth/authorize?{query_string}"
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/oauth/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": authorization_code,
                        "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/basalam/callback"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    return {
                        "access_token": token_data.get("access_token"),
                        "refresh_token": token_data.get("refresh_token"),
                        "token_type": token_data.get("token_type", "Bearer"),
                        "expires_in": token_data.get("expires_in", 3600),
                        "expires_at": datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
                    }
                else:
                    logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error exchanging authorization code: {str(e)}")
                return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/oauth/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    return {
                        "access_token": token_data.get("access_token"),
                        "refresh_token": token_data.get("refresh_token", refresh_token),
                        "token_type": token_data.get("token_type", "Bearer"),
                        "expires_in": token_data.get("expires_in", 3600),
                        "expires_at": datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
                    }
                else:
                    logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error refreshing token: {str(e)}")
                return None
    
    async def get_user_profile(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information from Basalam
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v1/user/profile",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user profile: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error getting user profile: {str(e)}")
                return None
    
    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if the access token is still valid
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v1/user/profile",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                return response.status_code == 200
                
            except Exception as e:
                logger.error(f"Error validating token: {str(e)}")
                return False
    
    async def store_user_tokens(self, db: AsyncSession, user_id: str, tokens: Dict[str, Any]) -> bool:
        """
        Store Basalam tokens for a user
        """
        try:
            # Update user with Basalam tokens
            stmt = update(User).where(User.id == user_id).values(
                basalam_access_token=tokens.get("access_token"),
                basalam_refresh_token=tokens.get("refresh_token"),
                basalam_token_expires_at=tokens.get("expires_at")
            )
            await db.execute(stmt)
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing user tokens: {str(e)}")
            await db.rollback()
            return False
    
    async def get_user_tokens(self, db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored Basalam tokens for a user
        """
        try:
            result = await db.execute(
                select(User.basalam_access_token, User.basalam_refresh_token, User.basalam_token_expires_at)
                .where(User.id == user_id)
            )
            row = result.first()
            
            if row and row[0]:  # access_token exists
                return {
                    "access_token": row[0],
                    "refresh_token": row[1],
                    "expires_at": row[2]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user tokens: {str(e)}")
            return None
    
    async def ensure_valid_token(self, db: AsyncSession, user_id: str) -> Optional[str]:
        """
        Ensure user has a valid access token, refresh if needed
        """
        tokens = await self.get_user_tokens(db, user_id)
        if not tokens:
            return None
        
        # Check if token is expired or close to expiring
        if tokens["expires_at"] and tokens["expires_at"] <= datetime.now() + timedelta(minutes=5):
            # Token is expired or close to expiring, try to refresh
            if tokens["refresh_token"]:
                new_tokens = await self.refresh_access_token(tokens["refresh_token"])
                if new_tokens:
                    await self.store_user_tokens(db, user_id, new_tokens)
                    return new_tokens["access_token"]
            return None
        
        return tokens["access_token"]