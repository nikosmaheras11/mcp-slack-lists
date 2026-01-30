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
# Default Slack List ID for the Project Tracker
DEFAULT_LIST_ID = os.getenv("SLACK_LIST_ID", "F0AC03K1EBE")

# Slack List Column IDs
COLUMNS = {
    "title": "Col0ABF27K66T",
    "description": "Col0ABQ4083FV", 
    "status": "Col0ABUDW1YH4",
    "priority": "Col0AC9D3FC57",
    "checkbox": "Col00",
}

# Map Notion statuses to Slack List option IDs
STATUS_MAPPING = {
    "Not started": "Opt7MNHB19N",
    "In progress": "OptXBPNOYKC", 
    "Done": "OptEY5M00J3",
}

# Map Notion priority to number (for Slack List)
PRIORITY_MAPPING = {
    "🔴 P1 - Urgent": 1,
    "🟡 P2 - High": 2,
    "🟢 P3 - Normal": 3,
}


async def find_item_by_title(list_id: str, title: str):
    """Find a Slack List item by its title"""
    client = get_slack_client()
    
    # Get all items and search for matching title
    all_items = await client.get_all_list_items(list_id)
    
    for item in all_items:
        for field in item.get("fields", []):
            if field.get("column_id") == COLUMNS["title"]:
                # Extract text value
                item_title = None
                if "text" in field:
                    item_title = field["text"]
                elif "value" in field:
                    item_title = field["value"]
                
                if item_title and item_title.strip().lower() == title.strip().lower():
                    return item
    
    return None


def build_cells_from_notion(body: dict) -> list:
    """Build Slack List cells from Notion webhook payload"""
    cells = []
    
    # Status
    status = body.get("Status") or body.get("status")
    if status and status in STATUS_MAPPING:
        cells.append({
            "column_id": COLUMNS["status"],
            "select": [STATUS_MAPPING[status]]
        })
    
    # Description/Details
    details = body.get("Details") or body.get("details")
    if details:
        cells.append({
            "column_id": COLUMNS["description"],
            "rich_text": [{
                "type": "rich_text",
                "elements": [{
                    "type": "rich_text_section",
                    "elements": [{"type": "text", "text": str(details)}]
                }]
            }]
        })
    
    # Priority
    priority = body.get("Priority") or body.get("priority")
    if priority and priority in PRIORITY_MAPPING:
        cells.append({
            "column_id": COLUMNS["priority"],
            "number": [PRIORITY_MAPPING[priority]]
        })
    
    return cells


async def notion_webhook(request: Request):
    """
    Webhook endpoint for Notion automations.
    Syncs any property changes from Notion to Slack Lists.
    Creates new items if they don't exist.
    
    Select "all existing properties" in Notion or pick specific ones.
    """
    try:
        body = await request.json()
        print(f"Received Notion webhook: {json.dumps(body, indent=2)}")
        
        # Extract title (required to find/create item)
        title = body.get("Request") or body.get("title") or body.get("name")
        list_id = body.get("list_id", DEFAULT_LIST_ID)
        
        if not title:
            return JSONResponse(
                {"error": "Missing 'Request' or 'title' in webhook payload"},
                status_code=400
            )
        
        client = get_slack_client()
        
        # Find existing item or create new one
        item = await find_item_by_title(list_id, title)
        
        if item:
            # UPDATE existing item
            item_id = item.get("id")
            cells = build_cells_from_notion(body)
            
            if cells:
                await client.update_list_item(list_id, item_id, cells)
                print(f"✅ Updated '{title}' with {len(cells)} field(s)")
            else:
                print(f"ℹ️ No fields to update for '{title}'")
            
            return JSONResponse({
                "success": True,
                "action": "updated",
                "message": f"Updated '{title}'",
                "item_id": item_id,
                "fields_updated": len(cells)
            })
        else:
            # CREATE new item
            from slack_lists_server import create_text_field, create_select_field
            
            fields = [create_text_field(COLUMNS["title"], title)]
            
            # Add status if provided
            status = body.get("Status") or body.get("status")
            if status and status in STATUS_MAPPING:
                fields.append(create_select_field(COLUMNS["status"], [STATUS_MAPPING[status]]))
            
            # Add details if provided
            details = body.get("Details") or body.get("details")
            if details:
                fields.append(create_text_field(COLUMNS["description"], str(details)))
            
            result = await client.create_list_item(list_id, fields)
            new_item_id = result.get("item", {}).get("id", "Unknown")
            
            print(f"✅ Created new item '{title}' (ID: {new_item_id})")
            
            return JSONResponse({
                "success": True,
                "action": "created",
                "message": f"Created '{title}'",
                "item_id": new_item_id
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
        import traceback
        traceback.print_exc()
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
