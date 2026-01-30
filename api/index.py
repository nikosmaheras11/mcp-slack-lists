#!/usr/bin/env python3
"""
Vercel serverless function for Slack Lists MCP Server
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from slack_lists_server import mcp

# Export the ASGI app for Vercel
app = mcp.sse_app()
