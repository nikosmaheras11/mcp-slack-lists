#!/usr/bin/env python3
"""
Vercel serverless function for Slack Lists MCP Server
Uses Streamable HTTP transport instead of SSE for better Vercel compatibility
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from slack_lists_server import mcp

# Export the ASGI app using streamable HTTP transport
# This is more compatible with serverless environments than SSE
app = mcp.streamable_http_app()
