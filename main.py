#!/usr/bin/env python3
"""
Main entry point for Railway deployment
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

from slack_lists_server import mcp

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Slack Lists MCP Server on {host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
