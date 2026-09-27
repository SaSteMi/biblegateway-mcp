"""
Authentik API client library for user and token management.

This module provides a Python client for interacting with the Authentik API
to manage users and API tokens.

Token Validation Workflow:
-------------------------
1. Token Creation:
     - Use the CLI command:
         uv run python tools/main.py generate-token <user_id> --name <token_name>
     - The response will include the secret token string. Save this value; it is only shown once.

2. Token Validation:
     - Use the CLI command:
         uv run python tools/main.py validate-token <actual_token_string>
     - The CLI calls AuthentikClient.validate_token(), which makes an authenticated 
       request to /api/v3/core/users/me/ using the token as the Authorization header.
     - If the token is valid, the response will include user info and 'active': True.
     - If the token is invalid, expired, or revoked, the response will include 'active': False.

Notes:
    - Always use the actual secret token string for validation, not the UUID or identifier.
    - API tokens are validated by making an authenticated API call, not via OAuth2 introspection.
    - The CLI supports user creation, token generation, and token validation.
    - Tokens are only shown once during creation - save them immediately.
"""

import requests
from typing import Dict


class AuthentikClient:
    """
    Client for interacting with Authentik API.
    
    This client provides methods for user management and API token operations
    using the Authentik authentication platform.
    
    Attributes:
        api_url (str): Base URL of the Authentik API (without trailing slash)
        token (str): Admin API token for authentication
        headers (dict): Default headers including Bearer token authentication
    """
    
    def __init__(self, api_url: str, token: str):
        """
        Initialize the Authentik API client.
        
        Args:
            api_url: Base URL of Authentik API (e.g., "http://authentik.example.com/api/v3")
            token: Admin API token for authentication
        """
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def create_user(self, username: str, name: str, email: str, password: str) -> Dict:
        """
        Create a new user in Authentik.
        
        Args:
            username: Unique username for the new user
            name: Full display name for the user
            email: Email address for the user
            password: Password for the user account
            
        Returns:
            dict: User object containing:
                - pk: User ID
                - username: Username
                - email: Email address
                - name: Display name
                - is_active: Whether user is active
                - uuid: User UUID
                
        Raises:
            requests.HTTPError: If the API request fails
        """
        url = f"{self.api_url}/api/v3/core/users/"
        payload = {
            "username": username,
            "name": name,
            "email": email,
            "password": password
        }
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def generate_token(self, user_id: str, name: str = "api-token") -> Dict:
        """
        Generate an API token for a user in Authentik.
        
        IMPORTANT: Authentik returns the token 'key' in the response only once.
        The 'key' field contains the actual Bearer token that must be saved immediately.
        You will not be able to retrieve it again after this call.
        
        Args:
            user_id: User ID (pk) to generate the token for
            name: Token name/identifier (default: "api-token")
            
        Returns:
            dict: Token object containing:
                - pk: Token UUID
                - key: The actual Bearer token (ONLY SHOWN ONCE!)
                - identifier: Token name/identifier
                - user: User ID this token belongs to
                - intent: Token purpose (always "api")
                - expiring: Whether token expires (False for API tokens)
                - expires: Expiration date if expiring=True
                
        Raises:
            requests.HTTPError: If the API request fails
            
        Note:
            If the 'key' field is missing from the response, check your Authentik
            version or configuration. Some versions may not return the key via API.
        """
        url = f"{self.api_url}/api/v3/core/tokens/"
        payload = {
            "user": user_id,
            "identifier": name,
            "intent": "api",
            "expiring": False
        }
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def validate_token(self, token: str) -> Dict:
        """
        Validate an API token by attempting to retrieve user information with it.
        
        This method tests if a token is valid and active by making an authenticated
        request to the /api/v3/core/users/me/ endpoint using the provided token.
        
        Args:
            token: The actual Bearer token string (the 'key' value from generate_token)
            
        Returns:
            dict: Validation result containing either:
                Success case:
                    - active (bool): True
                    - user (dict): User information including username, email, etc.
                    
                Failure case:
                    - active (bool): False
                    - status_code (int): HTTP status code
                    - detail (str): Error message
                    
        Example:
            >>> client = AuthentikClient(api_url, admin_token)
            >>> result = client.validate_token(user_token)
            >>> if result["active"]:
            ...     print(f"Token valid for user: {result['user']['username']}")
            ... else:
            ...     print(f"Token invalid: {result['detail']}")
        """
        url = f"{self.api_url}/api/v3/core/users/me/"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return {
                "active": True,
                "user": response.json()
            }
        else:
            return {
                "active": False,
                "status_code": response.status_code,
                "detail": response.text
            }