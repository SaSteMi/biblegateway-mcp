"""
Authentication dependencies for FastAPI routes using Authentik.

This module provides reusable authentication dependencies for protecting
FastAPI endpoints with Bearer token authentication validated via Authentik API.

Usage Example:
    from core.auth_rest import get_token_from_header
    
    @app.get("/protected")
    async def protected_route(user: dict = Depends(get_token_from_header)):
        return {"message": f"Hello {user['username']}"}
"""

from typing import Dict
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .authentik_client import AuthentikClient
from .config import AuthentikConfig

# HTTPBearer instance for extracting Bearer tokens from Authorization header
security = HTTPBearer()


def get_authentik_client() -> AuthentikClient:
    """
    Create and return an Authentik API client instance.
    
    This function retrieves Authentik configuration using AuthentikConfig
    and initializes the client. It's used as a FastAPI dependency.
    
    Returns:
        AuthentikClient: Configured Authentik API client
        
    Raises:
        RuntimeError: If AUTHENTIK_API_URL or AUTHENTIK_API_TOKEN are not set
        
    Example:
        >>> client = get_authentik_client()
        >>> result = client.validate_token(user_token)
    """
    try:
        config = AuthentikConfig.from_env()
        return AuthentikClient(config.api_url, config.api_token)
    except ValueError as e:
        raise RuntimeError(
            "Authentik configuration error: Authentication will not work. " + str(e)
        )
    
    return AuthentikClient(api_url, api_token)


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Security(security),
    client: AuthentikClient = Depends(get_authentik_client),
) -> Dict:
    """
    Validate Bearer token and return authenticated user information.
    
    This is the main authentication dependency for FastAPI routes.
    It extracts the Bearer token from the Authorization header,
    validates it against Authentik, and returns the user object.
    
    If authentication is disabled via configuration, this function 
    will return a mock user without validating the token.
    
    Args:
        credentials: Bearer token credentials from Authorization header
        client: Authentik API client (injected by dependency)
        
    Returns:
        dict: Authenticated user object containing:
            - pk: User ID
            - username: Username
            - email: Email address
            - name: Display name
            - is_active: Whether user is active
            - groups: List of user groups
            
    Raises:
        HTTPException: 401 if token is missing, empty, invalid, or inactive (when auth is enabled)
        
    Example:
        @app.get("/api/data")
        async def get_data(user: dict = Depends(get_token_from_header)):
            return {"data": "secret", "user": user["username"]}
    """
    # Check if authentication is enabled in configuration
    from mcp_bible.config import get_config
    auth_enabled = get_config().server.auth_enabled
    
    # If authentication is disabled, return a mock user without validation
    if not auth_enabled:
        import logging
        logging.getLogger(__name__).warning("⚠️ Authentication is DISABLED. Using mock user. Not secure for production!")
        return {
            "pk": 0,
            "username": "mock_user",
            "email": "mock@example.com",
            "name": "Authentication Disabled",
            "is_active": True,
            "groups": ["mock_users"]
        }
    
    # If we reach here, authentication is enabled - validate the token
    token_value = credentials.credentials
    
    if not token_value:
        raise HTTPException(
            status_code=401,
            detail="Token value is required"
        )
    
    # Validate token with Authentik API
    result = client.validate_token(token_value)
    
    if not result.get("active"):
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive token"
        )
    
    return result["user"]