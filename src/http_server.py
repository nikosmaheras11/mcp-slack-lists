#!/usr/bin/env python3
"""
HTTP wrapper for Slack Lists MCP Server

This adds HTTP transport to the existing STDIO-based MCP server,
enabling remote deployment for use with Claude's custom connector feature.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the existing MCP server
from slack_lists_server import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Validate environment
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        logger.error("SLACK_BOT_TOKEN environment variable is required")
        exit(1)

    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Slack Lists MCP Server with HTTP transport on {host}:{port}")
    logger.info("Available tools: create_list_item, create_multiple_list_items, get_list_items, filter_list_items, export_list_items")

    # Run with SSE transport for remote MCP
    mcp.run(transport="sse", host=host, port=port)
