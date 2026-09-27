"""
Core infrastructure shared across projects

This package contains reusable infrastructure components that can be
shared across multiple projects, including authentication, configuration,
and other common utilities.
"""

from .config import (
    AuthentikConfig,
    BaseCacheConfig,
    BaseServerConfig,
)

from .auth_rest import (
    get_authentik_client,
    get_token_from_header,
)

from .authentik_client import (
    AuthentikClient,
)

from .auth_mcp import (
    AuthInfo,
    AuthentikAuthProvider,
    create_auth_provider,
    get_auth_provider,
)

from .server import (
    BaseMCPServer,
    BaseService,
    create_server,
    create_standard_cli_parser,
    apply_cli_args_to_environment,
    create_main_with_modes,
)