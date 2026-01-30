#!/usr/bin/env python3
"""
Main entry point for Railway deployment
Uses FastMCP SSE transport for remote MCP connections
Includes webhook endpoint for Notion → Slack Lists sync
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.requests import Request
import json
import httpx

from slack_lists_server import mcp, get_slack_client, SlackListsError

# Configuration for Notion → Slack Lists sync
# Map your Notion statuses to Slack List option IDs
STATUS_MAPPING = {
    "Not started": "Opt7MNHB19N",
    "In progress": "OptXBPNOYKC",
    "Done": "OptEY5M00J3",
}

# Default Slack List ID for the Project Tracker
DEFAULT_LIST_ID = os.getenv("SLACK_LIST_ID", "F0AC03K1EBE")

# Column IDs
STATUS_COLUMN_ID = "Col0ABUDW1YH4"
TITLE_COLUMN_ID = "Col0ABF27K66T"


async def find_item_by_title(list_id: str, title: str):
    """Find a Slack List item by its title"""
    client = get_slack_client()
    
    # Get all items and search for matching title
    all_items = await client.get_all_list_items(list_id)
    
    for item in all_items:
        for field in item.get("fields", []):
            if field.get("column_id") == TITLE_COLUMN_ID:
                # Extract text value
                item_title = None
                if "text" in field:
                    item_title = field["text"]
                elif "value" in field:
                    item_title = field["value"]
                
                if item_title and item_title.strip().lower() == title.strip().lower():
                    return item
    
    return None


async def notion_webhook(request: Request):
    """
    Webhook endpoint for Notion automations.
    
    Expected payload from Notion:
    {
        "title": "Task name",
        "status": "In progress",
        "list_id": "F0AC03K1EBE" (optional, uses default if not provided)
    }
    """
    try:
        body = await request.json()
        print(f"Received Notion webhook: {json.dumps(body, indent=2)}")
        
        # Extract data from Notion payload
        title = body.get("title") or body.get("name") or body.get("Request")
        status = body.get("status") or body.get("Status")
        list_id = body.get("list_id", DEFAULT_LIST_ID)
        
        if not title:
            return JSONResponse(
                {"error": "Missing 'title' in webhook payload"},
                status_code=400
            )
        
        if not status:
            return JSONResponse(
                {"error": "Missing 'status' in webhook payload"},
                status_code=400
            )
        
        # Map Notion status to Slack option ID
        slack_option_id = STATUS_MAPPING.get(status)
        if not slack_option_id:
            return JSONResponse(
                {"error": f"Unknown status: {status}. Valid statuses: {list(STATUS_MAPPING.keys())}"},
                status_code=400
            )
        
        # Find the item in Slack List by title
        item = await find_item_by_title(list_id, title)
        if not item:
            return JSONResponse(
                {"error": f"Item not found in Slack List: {title}"},
                status_code=404
            )
        
        item_id = item.get("id")
        
        # Update the status
        client = get_slack_client()
        cells = [{
            "column_id": STATUS_COLUMN_ID,
            "select": [slack_option_id]
        }]
        
        await client.update_list_item(list_id, item_id, cells)
        
        print(f"✅ Updated '{title}' status to '{status}' (option: {slack_option_id})")
        
        return JSONResponse({
            "success": True,
            "message": f"Updated '{title}' status to '{status}'",
            "item_id": item_id,
            "list_id": list_id
        })
        
    except json.JSONDecodeError:
        return JSONResponse(
            {"error": "Invalid JSON in request body"},
            status_code=400
        )
    except SlackListsError as e:
        print(f"❌ Slack Lists error: {e}")
        return JSONResponse(
            {"error": f"Slack Lists error: {str(e)}"},
            status_code=500
        )
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return JSONResponse(
            {"error": f"Internal error: {str(e)}"},
            status_code=500
        )


async def health_check(request: Request):
    """Health check endpoint"""
    return JSONResponse({"status": "ok", "service": "slack-lists-mcp"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Slack Lists MCP Server on {host}:{port}")
    print("Available tools: create_list_item, create_multiple_list_items, get_list_items, filter_list_items, export_list_items, update_list_item")
    print(f"SSE endpoint: http://{host}:{port}/sse")
    print(f"Webhook endpoint: http://{host}:{port}/webhook/notion")

    # Get the SSE app and add custom routes
    app = mcp.sse_app()
    
    # Add webhook and health routes
    app.routes.append(Route("/webhook/notion", notion_webhook, methods=["POST"]))
    app.routes.append(Route("/health", health_check, methods=["GET"]))
    
    uvicorn.run(app, host=host, port=port)
