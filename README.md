> [!note]
> This is a fork I made and published to PyPI cause I felt like it. Basically equal to [geosp/mcp-bible](https://github.com/geosp/mcp-bible), go read the documentation there.

# BibleGateway MCP Server

A Model Context Protocol (MCP) server that provides Bible passage retrieval functionality using the `mcp-weather` core infrastructure.

This server enables AI assistants to access Bible passages from various translations, with support for multiple deployment modes:

- **`--mode stdio`** (default): MCP protocol over stdin/stdout for direct AI assistant integration
- **`--mode mcp`**: MCP protocol over HTTP for networked AI assistant access  
- **`--mode rest`**: Both REST API and MCP protocol over HTTP for maximum flexibility

## Features

The BibleGateway MCP Server provides:

### MCP Tools (for AI assistants)
- `get_passage(passage, version)` - Retrieve Bible passages. Supports multiple passages separated by semicolons (e.g., "John 3:16; Romans 8:28").

### REST API Endpoints
- `GET /health` - Health check
- `GET /info` - Service information
- `POST /passage` - Get Bible passage
- `GET /docs` - OpenAPI documentation (Swagger UI)

### Supported Bible Versions
Supports all translations available on BibleGateway.com (200+ versions across 70+ languages). Common examples include:
- ESV (English Standard Version) - Default
- NIV (New International Version)
- KJV (King James Version)
- NASB (New American Standard Bible)
- NKJV (New King James Version)
- NLT (New Living Translation)
- AMP (Amplified Bible)
- MSG (The Message)
- CSB (Christian Standard Bible)
- NRSVUE (New Revised Standard Version Updated Edition)
- Any other valid BibleGateway code (e.g. `LUT` for German Luther, `LSG` for French Louis Segond, etc.)

## Installation

### Prerequisites
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

### Install

```bash
uv tool install biblegateway-mcp
```

## Usage

The BibleGateway MCP server supports three deployment modes via command-line arguments:

### Mode 1: stdio (Default) - Direct AI Assistant Integration

```bash
# Default mode - MCP over stdin/stdout
bg-mcp

# Explicitly specify stdio mode  
bg-mcp --mode stdio
```

Perfect for direct integration with AI assistants like GitHub Copilot, Claude Desktop, etc.

### Mode 2: mcp - MCP Protocol over HTTP

```bash
# MCP-only server on HTTP (no REST API)
bg-mcp --mode mcp --port 3000 --no-auth
```

Provides MCP protocol over HTTP at `http://localhost:3000/mcp` for networked AI assistant access.

### Mode 3: rest - Full HTTP Server (REST + MCP)

```bash
# Full server with both REST API and MCP protocol
bg-mcp --mode rest --port 3000 --no-auth
```

The server will start at `http://localhost:3000` with:
- MCP endpoint: `http://localhost:3000/mcp`
- REST API: `http://localhost:3000/*`
- API docs: `http://localhost:3000/docs`
- Health check: `http://localhost:3000/health`

### Test the MCP Tools

You can test the MCP tools by connecting GitHub Copilot or using a test client:

```json
// .vscode/mcp.json
{
  "servers": {
    "bible": {
      "type": "http",
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

Then ask Copilot:
- "Show me John 3:16"
- "What does Romans 8 say?"
- "Read Psalm 23 in NIV"

### Test the REST API

```bash
# Health check
curl http://localhost:3000/health

# Get service info
curl http://localhost:3000/info

# Get a Bible passage
curl -X POST "http://localhost:3000/passage" \
  -H "Content-Type: application/json" \
  -d '{
    "passage": "John 3:16",
    "version": "ESV"
  }'

# Get multiple passages
curl -X POST "http://localhost:3000/passage" \
  -H "Content-Type: application/json" \
  -d '{
    "passage": "John 3:16; Romans 8:28; Philippians 4:13",
    "version": "NIV"
  }'

# Get an entire chapter
curl -X POST "http://localhost:3000/passage" \
  -H "Content-Type: application/json" \
  -d '{
    "passage": "Mark 2",
    "version": "ESV"
  }'
```

### CLI Help and Options

```bash
# See all available options
bg-mcp --help

# Usage examples:
bg-mcp                         # stdio mode (default)
bg-mcp --mode stdio            # stdio mode
bg-mcp --mode mcp --port 4000  # MCP-only HTTP on port 4000
bg-mcp --mode rest --port 4000 # REST+MCP HTTP on port 4000
bg-mcp --mode rest --no-auth   # Disable authentication
```

### Environment Variables (Alternative to CLI)

You can also configure the server using environment variables:

```bash
# Alternative: Set environment variables
export MCP_TRANSPORT=http        # stdio or http
export MCP_ONLY=false           # true for MCP-only, false for REST+MCP
export MCP_HOST=0.0.0.0         # Host to bind to
export MCP_PORT=3000            # Port number
export AUTH_ENABLED=false       # Enable/disable authentication

# Then run without arguments
bg-mcp
```

## License for original code from geosp/mcp-bible

This project is provided as-is for use and modification.
