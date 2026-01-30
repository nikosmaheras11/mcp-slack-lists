#!/usr/bin/env python3
"""
Main entry point for Railway deployment
Uses Starlette with SSE app for remote MCP connections
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import PlainTextResponse
from slack_lists_server import mcp

# Health check endpoint
async def health(request):
    return PlainTextResponse("OK - Slack Lists MCP Server Running")

# Root endpoint
async def root(request):
    return PlainTextResponse("Slack Lists MCP Server\n\nEndpoints:\n- /sse - MCP SSE endpoint\n- /health - Health check")

# Create the main app with health check and mount SSE
app = Starlette(
    routes=[
        Route("/", root),
        Route("/health", health),
        Mount("/", app=mcp.sse_app()),
    ]
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Slack Lists MCP Server on {host}:{port}")
    print("Available tools: create_list_item, create_multiple_list_items, get_list_items, filter_list_items, export_list_items")
    print(f"SSE endpoint: http://{host}:{port}/sse")

    uvicorn.run(app, host=host, port=port)
