#!/usr/bin/env python3
"""
Main entry point for Railway deployment
Uses FastMCP SSE transport for remote MCP connections
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from slack_lists_server import mcp

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Slack Lists MCP Server on {host}:{port}")
    print("Available tools: create_list_item, create_multiple_list_items, get_list_items, filter_list_items, export_list_items")
    print(f"SSE endpoint: http://{host}:{port}/sse")

    # Get the SSE app and run with uvicorn
    app = mcp.sse_app()
    uvicorn.run(app, host=host, port=port)
