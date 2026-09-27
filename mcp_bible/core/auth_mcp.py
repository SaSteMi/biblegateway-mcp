"""
Reusable Authentik authentication provider for MCP services

This module provides a ready-to-use Authentik authentication provider for FastMCP.
It integrates with the existing Authentik client to validate tokens and extract user information.
"""

import logging
import flatdict
from typing import Optional, List, Dict, Any

from fastmcp.server.auth import AuthProvider
from .auth_rest import get_authentik_client

logger = logging.getLogger(__name__)


class AuthInfo:
    """
    Flexible authentication information that accepts any attributes.
    
    This class dynamically accepts any field returned by Authentik's token
    introspection and makes them accessible as attributes.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize with any keyword arguments.
        
        Args:
            **kwargs: Any authentication fields from token introspection
        """
        # Set all provided attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # Ensure required attributes have defaults
        if not hasattr(self, 'client_id'):
            self.client_id = ""
        if not hasattr(self, 'scopes'):
            self.scopes = []
        if not hasattr(self, 'expires_at'):
            self.expires_at = None
        if not hasattr(self, 'user'):
            self.user = ""
        if not hasattr(self, 'user_id'):
            self.user_id = ""
    
    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"AuthInfo({attrs})"


class AuthentikAuthProvider(AuthProvider):
    """
    Authentik authentication provider for FastMCP
    
    This provider integrates with the Authentik API to validate tokens
    for FastMCP services. It's designed to be reused across multiple projects.
    
    Architecture:
        FastMCP Auth Protocol -> AuthentikAuthProvider -> AuthentikClient -> Authentik API
    
    Usage:
        auth_provider = create_auth_provider()
        mcp = FastMCP("my-service", auth=auth_provider)
    """
    
    # Required by FastMCP - scopes needed for authentication
    required_scopes: List[str] = []
    
    # Required by FastMCP - base URL for OAuth metadata
    base_url: Optional[str] = None
    
    def __init__(self, service_name: str = "service"):
        """
        Initialize Authentik auth provider
        
        Args:
            service_name: Name of the service using this auth provider (for logging)
        """
        self.service_name = service_name
        # Get Authentik client using the existing factory function
        self.client = get_authentik_client()
        logger.info(f"Initialized AuthentikAuthProvider for {service_name}")
    
    async def __call__(self, token: str) -> Optional[AuthInfo]:
        """
        Verify a Bearer token with Authentik (FastMCP auth callback)
        
        This method is called by FastMCP's auth middleware to validate tokens.
        It uses your existing AuthentikClient.validate_token() method.
        
        Args:
            token: Bearer token string to verify
            
        Returns:
            AuthInfo object with user info if valid, None if invalid
            
        Note:
            FastMCP expects this to be an async callable that returns
            an object with user info or None for invalid tokens.
        """
        return await self.verify_token(token)
    
    async def verify_token(self, token: str) -> Optional[AuthInfo]:
        """
        Verify a Bearer token with Authentik
        
        Args:
            token: Bearer token string to verify
            
        Returns:
            AuthInfo object with user info if valid, None if invalid
        """
        try:
            # Use token validation from AuthentikClient
            result = self.client.validate_token(token)
            
            if not result.get("active"):
                logger.warning(f"Invalid or inactive token: {token[:20]}...")
                return None
            
            # Extract user information from auth result
            user = flatdict.FlatDict(result.get("user", {}), delimiter='.')
            username = user.get("user.username")
            
            logger.info(f"✓ Authenticated {self.service_name} request for user: {username}")
            
            # Get token metadata
            expires_at = result.get("exp")
            scopes_str = result.get("scope", "")
            scopes = scopes_str.split() if scopes_str else []
            client_id = result.get("client_id", "")
            
            # Return flexible AuthInfo with all available fields
            return AuthInfo(
                user=username,
                user_id=str(user.get("pk", "")),
                email=user.get("email", ""),
                name=user.get("name", ""),
                is_active=user.get("is_active", False),
                groups=user.get("groups", []),
                client_id=client_id,
                scopes=scopes,
                expires_at=expires_at,
                # Pass through any other fields from Authentik
                **{k: v for k, v in result.items() if k not in ['active', 'user']}
            )
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None


# Global auth provider instance
_auth_provider: Optional[AuthentikAuthProvider] = None


def create_auth_provider(service_name: str = "service") -> AuthentikAuthProvider:
    """
    Create a new Authentik auth provider instance
    
    Note: In most cases, you should use get_auth_provider() instead to take
    advantage of the singleton pattern, which reuses a single instance.
    Only use this function directly when you explicitly need a new instance.
    
    Args:
        service_name: Name of the service using this auth provider
        
    Returns:
        AuthentikAuthProvider: New auth provider instance
    """
    return AuthentikAuthProvider(service_name)


def get_auth_provider(service_name: str = "service") -> AuthentikAuthProvider:
    """
    Get or create a global Authentik auth provider instance (SINGLETON PATTERN)
    
    This function implements the singleton pattern for the auth provider.
    The first call will create the provider, subsequent calls return the same instance.
    This is the PREFERRED way to get an auth provider as it ensures only one
    instance is created and reused across the application, which saves resources
    and ensures consistent authentication state.
    
    Args:
        service_name: Name of the service using this auth provider
        
    Returns:
        AuthentikAuthProvider: Shared auth provider instance
    """
    global _auth_provider
    
    if _auth_provider is None:
        logger.info(f"Creating singleton auth provider for {service_name}")
        _auth_provider = create_auth_provider(service_name)
    else:
        logger.debug(f"Reusing existing auth provider for {service_name}")
        
    return _auth_provider