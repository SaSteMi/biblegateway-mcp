# Core Infrastructure

This directory contains reusable infrastructure components that can be shared across multiple projects.

## Components

### 1. Server Infrastructure

- **server.py**: Base server classes and factory functions:
  - `BaseService`: Abstract base class for service implementations
  - `BaseMCPServer`: Abstract base class for MCP server implementation
  - Support for both MCP-only mode and combined REST+MCP mode
  - Factory functions for creating server instances

### 2. Authentication

- **auth_rest.py**: FastAPI authentication dependencies for REST API with Authentik
- **auth_mcp.py**: MCP authentication providers for FastMCP integration
- **authentik_client.py**: Client for interacting with Authentik API

### 3. Configuration

- **config.py**: Base configuration classes for common settings like:
  - Authentication settings
  - Cache settings
  - Server settings
  - Redis settings

### 4. Caching

- **cache.py**: Redis-based caching infrastructure:
  - `RedisCacheClient`: Async Redis client with error handling
  - `EnhancedJsonSerializer`: Custom JSON serializer for complex objects
  - Comprehensive error handling for Redis connection issues

## Usage

### Authentication

```python
# Get a ready-to-use Authentik auth provider
from core.auth_mcp import get_auth_provider
auth_provider = get_auth_provider("my-service")

# Or create a new instance
from core.auth_mcp import create_auth_provider
auth_provider = create_auth_provider("my-service")

# Use with FastMCP
from fastmcp import FastMCP
mcp = FastMCP("my-service", auth=auth_provider)
```

### Configuration

```python
# Extend base configuration classes
from core.config import BaseServerConfig

class MyServerConfig(BaseServerConfig):
    # Add custom fields
    debug_mode: bool = False
    
    @classmethod
    def from_env(cls):
        config = super().from_env(env_prefix="MY_APP_")
        config.debug_mode = os.getenv("MY_APP_DEBUG", "false").lower() == "true"
        return config
```

### Redis Cache

```python
# Use the Redis cache client
import asyncio
from core.cache import RedisCacheClient
from core.config import RedisCacheConfig

async def cache_example():
    # Create cache configuration
    cache_config = RedisCacheConfig(
        host="redis.example.com",
        port=6379,
        db=0,
        password="optional_password",
        namespace="my-service",
        ttl=3600  # 1 hour TTL in seconds
    )
    
    # Initialize cache client
    cache_client = RedisCacheClient(cache_config)
    
    # Store data
    await cache_client.set("user:123", {"name": "John", "email": "john@example.com"})
    
    # Retrieve data with custom deserializer
    class User:
        def __init__(self, name, email):
            self.name = name
            self.email = email
    
    def user_deserializer(data):
        return User(data["name"], data["email"])
    
    user = await cache_client.get("user:123", user_deserializer)
    
    # Delete data
    await cache_client.delete("user:123")
```

### Server Implementation

```python
# Create a service implementation
from core.server import BaseService
from fastmcp import FastMCP

class MyService(BaseService):
    def initialize(self) -> None:
        # Initialize service resources
        pass
        
    def get_service_name(self) -> str:
        return "my-service"
        
    def register_mcp_tools(self, mcp: FastMCP) -> None:
        # Register MCP tools
        pass
        
    def cleanup(self) -> None:
        # Clean up resources
        pass

# Create a server implementation
from core.server import BaseMCPServer
from fastapi import APIRouter, FastAPI

class MyMCPServer(BaseMCPServer):
    @property
    def service_title(self) -> str:
        return "My MCP Service"
    
    @property
    def service_description(self) -> str:
        return "MCP service for my application"
    
    @property
    def service_version(self) -> str:
        return "1.0.0"
    
    @property
    def allowed_cors_origins(self) -> List[str]:
        return ["*"]  # Configure appropriately for production
    
    def create_auth_provider(self) -> Optional[Any]:
        # Create authentication provider
        pass
    
    def create_router(self) -> APIRouter:
        # Create REST API router
        router = APIRouter()
        return router
    
    def register_exception_handlers(self, app: FastAPI) -> None:
        # Register exception handlers
        pass

# Create and run the server
from core.server import create_server
from my_config import MyConfig

config = MyConfig.from_env()
service = MyService()
server = create_server(MyMCPServer, config, service)
server.run()  # Will use MCP-only or REST+MCP mode based on config
```

## Design Principles

1. **Reusability**: Components should be designed for reuse across projects
2. **Extensibility**: Base classes and interfaces should be easy to extend
3. **Separation of Concerns**: Clear boundaries between different components
4. **Consistency**: Common patterns and interfaces for similar tasks
5. **Documentation**: Clear documentation for all components