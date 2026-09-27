"""
BibleGateway MCP Server

This demonstrates how to create a complete MCP server by extending
BaseMCPServer from the mcp-weather core infrastructure.
"""

import logging
import sys
from typing import List, Optional, Any

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from mcp_bible.core.server import BaseMCPServer
from mcp_bible.core.auth_mcp import create_auth_provider
from mcp_bible.core.cache import RedisCacheClient

from mcp_bible.config import AppConfig, get_config
from mcp_bible.bible_service import BibleService
from mcp_bible.service import BibleMCPService

logger = logging.getLogger(__name__)


class BibleMCPServer(BaseMCPServer):
    """
    Bible MCP Server implementation

    Extends BaseMCPServer to provide Bible functionality via MCP protocol.
    This shows how to implement all required abstract methods.
    """

    @property
    def service_title(self) -> str:
        """Title shown in API documentation"""
        return "BibleGateway MCP Server"

    @property
    def service_description(self) -> str:
        """Description shown in API documentation"""
        return (
            "Provides Bible passage retrieval capabilities via Model Context Protocol (MCP). "
            "Supports multiple Bible translations with automatic parsing and cleaning."
        )

    @property
    def service_version(self) -> str:
        """Service version"""
        return "1.0.0"

    @property
    def allowed_cors_origins(self) -> List[str]:
        """CORS origins for web clients"""
        # Use CORS origins from configuration
        if hasattr(self.config, "server") and hasattr(self.config.server, "cors_origins"):
            return self.config.server.cors_origins
        # Fallback to default values if not configured
        return [
            "http://localhost:3000",
            "http://localhost:8080"
        ]

    def create_auth_provider(self) -> Optional[Any]:
        """
        Create authentication provider for this server

        Returns None to disable auth, or create an Authentik provider
        """
        # Check if authentication is enabled using flattened config
        auth_enabled = self.get_config("server.auth_enabled", self.get_config("auth_enabled", True))
        
        if not auth_enabled:
            logger.info("Authentication is disabled")
            return None

        if not self.config.authentik:
            logger.warning("Authentication enabled but no Authentik config found")
            return None

        logger.info("Creating Authentik authentication provider")
        return create_auth_provider("bible")

    def create_router(self) -> APIRouter:
        """
        Create REST API router with endpoints

        Uses feature-based organization - each feature has its own routes.py
        This demonstrates automatic feature route discovery and composition.
        """
        import importlib
        import pkgutil
        from pathlib import Path

        # Create main router
        router = APIRouter()

        # Access the bible service through the MCP service wrapper
        bible_service = self.service.bible_service

        # Add base routes (health, info)
        @router.get("/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "bible",
                "version": self.service_version
            }

        @router.get("/info")
        async def info():
            """Service information endpoint"""
            return {
                "title": self.service_title,
                "description": self.service_description,
                "version": self.service_version,
                "supported_versions": self.config.bible_api.supported_versions
            }

        # Discover and include feature routes
        features_package = "mcp_bible.features"
        features_path = Path(__file__).parent / "features"

        if features_path.exists():
            for _, feature_name, is_pkg in pkgutil.iter_modules([str(features_path)]):
                if not is_pkg:
                    continue

                try:
                    # Import the routes module from the feature
                    routes_module_name = f"{features_package}.{feature_name}.routes"
                    routes_module = importlib.import_module(routes_module_name)

                    # Check if the module has a create_router function
                    if hasattr(routes_module, "create_router"):
                        # Create and include the feature router
                        feature_router = routes_module.create_router(bible_service)
                        router.include_router(feature_router)
                        logger.info(f"✓ Included routes from feature: {feature_name}")
                except ModuleNotFoundError:
                    # Feature doesn't have routes.py, skip it
                    logger.debug(f"Feature '{feature_name}' has no routes.py, skipping")
                except Exception as e:
                    logger.error(f"Error including routes from feature '{feature_name}': {e}")
        return router

    def register_exception_handlers(self, app: FastAPI) -> None:
        """
        Register custom exception handlers

        This demonstrates how to add service-specific error handling.
        """
        from fastapi import Request
        from fastapi.responses import JSONResponse

        @app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            """Handle validation errors"""
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation Error",
                    "detail": str(exc)
                }
            )

        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle unexpected errors"""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred"
                }
            )

def main():
    """
    Main entry point for the Bible server with mode support

    Supports three modes:
    - stdio (default): MCP over stdin/stdout  
    - mcp: MCP protocol over HTTP (no REST API)
    - rest: Both REST API and MCP protocol over HTTP
    
    Usage:
        bg-mcp                    # stdio mode (default)
        bg-mcp --mode stdio       # stdio mode  
        bg-mcp --mode mcp         # MCP-only over HTTP
        bg-mcp --mode rest        # REST API + MCP over HTTP
    """
    import argparse
    import os
    
    try:
        # Create CLI parser with mode support
        parser = argparse.ArgumentParser(
            description="BibleGateway MCP Server",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  bg-mcp                         # Run with stdio transport (default)
  bg-mcp --mode stdio            # Run with stdio transport
  bg-mcp --mode mcp --port 3000  # Run MCP-only server on port 3000
  bg-mcp --mode rest --port 3000 # Run REST API + MCP server on port 3000
  
Environment Variables:
  MCP_TRANSPORT          Transport mode: stdio or http
  MCP_HOST              Host to bind to for HTTP modes (default: 0.0.0.0)
  MCP_PORT              Port to bind to for HTTP modes (default: 3000)
  MCP_ONLY              true for MCP-only, false for REST+MCP
  AUTH_ENABLED          Enable authentication for HTTP modes
            """
        )
        
        # Mode selection
        parser.add_argument(
            "--mode",
            choices=["stdio", "mcp", "rest"],
            default="stdio",
            help="Server mode: stdio (default), mcp (HTTP MCP-only), or rest (HTTP with REST API + MCP)"
        )
        
        # Host and port for HTTP modes
        parser.add_argument(
            "--host", 
            default="0.0.0.0",
            help="Host to bind to for HTTP modes (default: 0.0.0.0)"
        )
        
        parser.add_argument(
            "--port", 
            type=int, 
            default=3000,
            help="Port to bind to for HTTP modes (default: 3000)"
        )
        
        # Authentication control
        parser.add_argument(
            "--no-auth",
            action="store_true",
            help="Disable authentication for HTTP modes (not recommended for production)"
        )
        
        args = parser.parse_args()
        
        # Apply CLI arguments to environment variables
        if args.mode == "stdio":
            os.environ["MCP_TRANSPORT"] = "stdio"
            os.environ["MCP_ONLY"] = "true"
        elif args.mode == "mcp":
            os.environ["MCP_TRANSPORT"] = "http"
            os.environ["MCP_ONLY"] = "true"
            os.environ["MCP_HOST"] = args.host
            os.environ["MCP_PORT"] = str(args.port)
            if args.no_auth:
                os.environ["AUTH_ENABLED"] = "false"
        elif args.mode == "rest":
            os.environ["MCP_TRANSPORT"] = "http"
            os.environ["MCP_ONLY"] = "false"
            os.environ["MCP_HOST"] = args.host
            os.environ["MCP_PORT"] = str(args.port)
            if args.no_auth:
                os.environ["AUTH_ENABLED"] = "false"

        # Load configuration from environment (after setting env vars)
        logger.info("Loading configuration...")
        config = get_config()

        # Create Redis cache client
        logger.info("Initializing Redis cache...")
        cache_client = RedisCacheClient(config.redis_cache)

        # Create bible service (business logic)
        logger.info("Initializing Bible service...")
        bible_service = BibleService(
            timeout=config.bible_api.timeout
        )

        # Create MCP service wrapper
        logger.info("Creating MCP service wrapper...")
        mcp_service = BibleMCPService(bible_service)

        # Create and run server
        logger.info("Creating server...")
        server = BibleMCPServer(config, mcp_service)

        logger.info("Starting server...")
        server.run()  # Core framework handles mode detection from env vars

    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
