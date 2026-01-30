#!/usr/bin/env python3
"""
Slack Lists MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with tools to interact 
with Slack Lists. This server enables creating, reading, updating, and managing Slack List 
items through standardized MCP tools.

Features:
- Create single or multiple list items
- Export and filter list items  
- Search and query list data
- Manage list metadata
- Support for all Slack List field types

Author: MCP Slack Lists Server
License: MIT
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import asyncio

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Try to import TransportSecuritySettings for disabling DNS rebinding protection
try:
    from mcp.server.transport_security import TransportSecuritySettings
    SECURITY_SETTINGS = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )
except ImportError:
    SECURITY_SETTINGS = None

# Configure logging to stderr (never stdout for MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server with security settings for remote deployment
if SECURITY_SETTINGS:
    mcp = FastMCP("slack-lists", transport_security=SECURITY_SETTINGS)
else:
    mcp = FastMCP("slack-lists")

# Slack API configuration
SLACK_API_BASE = "https://slack.com/api"
DEFAULT_TIMEOUT = 30.0

class SlackListsError(Exception):
    """Custom exception for Slack Lists operations"""
    pass

class SlackListsClient:
    """Client for interacting with Slack Lists API"""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "slack-lists-mcp-server/1.0"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Slack API"""
        url = f"{SLACK_API_BASE}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers, params=kwargs.get('params'))
                else:
                    response = await client.request(
                        method, url, headers=self.headers, 
                        json=kwargs.get('json'), params=kwargs.get('params')
                    )
                
                response.raise_for_status()
                data = response.json()
                
                if not data.get("ok"):
                    raise SlackListsError(f"Slack API error: {data.get('error', 'Unknown error')}")
                
                return data
                
            except httpx.HTTPError as e:
                raise SlackListsError(f"HTTP error: {str(e)}")
            except Exception as e:
                raise SlackListsError(f"Request failed: {str(e)}")
    
    async def create_list_item(self, list_id: str, fields: List[Dict[str, Any]], 
                              parent_item_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new item in a Slack List"""
        payload = {
            "list_id": list_id,
            "initial_fields": fields
        }
        
        if parent_item_id:
            payload["parent_item_id"] = parent_item_id
        
        return await self._make_request("POST", "slackLists.items.create", json=payload)
    
    async def get_list_items(self, list_id: str, limit: int = 100, 
                           cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get items from a Slack List with pagination"""
        params = {"list_id": list_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        
        return await self._make_request("GET", "slackLists.items.list", params=params)
    
    async def get_all_list_items(self, list_id: str) -> List[Dict[str, Any]]:
        """Get all items from a Slack List (handles pagination)"""
        all_items = []
        cursor = None
        
        while True:
            data = await self.get_list_items(list_id, cursor=cursor)
            items = data.get("items", [])
            all_items.extend(items)
            
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        
        return all_items

# Global client instance (will be initialized with token)
slack_client: Optional[SlackListsClient] = None

def get_slack_client() -> SlackListsClient:
    """Get or create Slack client instance"""
    global slack_client
    
    if slack_client is None:
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            raise SlackListsError(
                "SLACK_BOT_TOKEN environment variable is required. "
                "Please set it to your Slack bot token with lists:read and lists:write scopes."
            )
        slack_client = SlackListsClient(token)
    
    return slack_client

def create_text_field(column_id: str, text: str) -> Dict[str, Any]:
    """Helper to create a rich text field"""
    return {
        "column_id": column_id,
        "rich_text": [{
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": [{
                    "type": "text",
                    "text": text
                }]
            }]
        }]
    }

def create_date_field(column_id: str, date: str) -> Dict[str, Any]:
    """Helper to create a date field (YYYY-MM-DD format)"""
    return {
        "column_id": column_id,
        "date": [date]
    }

def create_user_field(column_id: str, user_ids: List[str]) -> Dict[str, Any]:
    """Helper to create a user field"""
    return {
        "column_id": column_id,
        "user": user_ids
    }

def create_select_field(column_id: str, option_ids: List[str]) -> Dict[str, Any]:
    """Helper to create a select field"""
    return {
        "column_id": column_id,
        "select": option_ids
    }

def create_checkbox_field(column_id: str, checked: bool) -> Dict[str, Any]:
    """Helper to create a checkbox field"""
    return {
        "column_id": column_id,
        "checkbox": checked
    }

def extract_field_value(item: Dict[str, Any], column_id: str) -> Any:
    """Extract the value of a specific field from an item"""
    fields = item.get("fields", [])
    
    for field in fields:
        if field.get("column_id") == column_id:
            # Try different value formats
            if "text" in field:
                return field["text"]
            elif "value" in field:
                return field["value"]
            elif "date" in field and field["date"]:
                return field["date"][0] if field["date"] else None
            elif "user" in field and field["user"]:
                return field["user"]
            elif "select" in field and field["select"]:
                return field["select"]
            elif "checkbox" in field:
                return field["checkbox"]
            elif "number" in field and field["number"]:
                return field["number"][0] if field["number"] else None
            elif "email" in field and field["email"]:
                return field["email"][0] if field["email"] else None
            elif "phone" in field and field["phone"]:
                return field["phone"][0] if field["phone"] else None
            else:
                return field.get("value")
    
    return None

# MCP Tools Implementation

@mcp.tool()
async def create_list_item(
    list_id: str,
    title: str,
    title_column_id: str = "Col10000000",
    additional_fields: Optional[str] = None,
    parent_item_id: Optional[str] = None
) -> str:
    """Create a new item in a Slack List.
    
    This tool creates a single item in the specified Slack List. The item must have at least
    a title field, and can include additional fields as needed. All field values are validated
    against the list's schema.
    
    Args:
        list_id: The ID of the Slack List (format: F1234ABCD)
        title: The main title/text for the item
        title_column_id: Column ID for the title field (default: Col10000000)
        additional_fields: JSON string of additional fields in format:
                          [{"column_id": "Col123", "type": "text", "value": "text"},
                           {"column_id": "Col456", "type": "date", "value": "2024-12-31"}]
        parent_item_id: Optional parent item ID to create a subtask
    
    Returns:
        Success message with the created item ID and details
    """
    try:
        client = get_slack_client()
        
        # Create the title field
        fields = [create_text_field(title_column_id, title)]
        
        # Parse and add additional fields if provided
        if additional_fields:
            try:
                extra_fields = json.loads(additional_fields)
                for field_def in extra_fields:
                    column_id = field_def["column_id"]
                    field_type = field_def["type"]
                    value = field_def["value"]
                    
                    if field_type == "text":
                        fields.append(create_text_field(column_id, value))
                    elif field_type == "date":
                        fields.append(create_date_field(column_id, value))
                    elif field_type == "user":
                        user_ids = value if isinstance(value, list) else [value]
                        fields.append(create_user_field(column_id, user_ids))
                    elif field_type == "select":
                        option_ids = value if isinstance(value, list) else [value]
                        fields.append(create_select_field(column_id, option_ids))
                    elif field_type == "checkbox":
                        fields.append(create_checkbox_field(column_id, bool(value)))
                    else:
                        logger.warning(f"Unsupported field type: {field_type}")
                        
            except json.JSONDecodeError as e:
                return f"Error parsing additional_fields JSON: {str(e)}"
        
        # Create the item
        result = await client.create_list_item(list_id, fields, parent_item_id)
        
        item = result.get("item", {})
        item_id = item.get("id", "Unknown")
        created_date = datetime.fromtimestamp(item.get("date_created", 0)).isoformat()
        
        return f"✅ Successfully created list item!\n" \
               f"Item ID: {item_id}\n" \
               f"List ID: {list_id}\n" \
               f"Title: {title}\n" \
               f"Created: {created_date}\n" \
               f"Fields: {len(fields)} field(s) added"
        
    except SlackListsError as e:
        return f"❌ Slack Lists error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in create_list_item: {str(e)}")
        return f"❌ Unexpected error: {str(e)}"

@mcp.tool()
async def create_multiple_list_items(
    list_id: str,
    items_data: str,
    title_column_id: str = "Col10000000",
    rate_limit_delay: float = 1.2
) -> str:
    """Create multiple items in a Slack List with rate limiting.
    
    This tool allows bulk creation of list items. Each item is created individually with
    proper rate limiting to respect Slack's API limits (~50 requests per minute).
    
    Args:
        list_id: The ID of the Slack List (format: F1234ABCD)
        items_data: JSON array of items to create. Format:
                   [{"title": "Item 1", "fields": [{"column_id": "Col123", "type": "text", "value": "value1"}]},
                    {"title": "Item 2", "fields": [{"column_id": "Col123", "type": "date", "value": "2024-12-31"}]}]
        title_column_id: Column ID for the title field (default: Col10000000)
        rate_limit_delay: Delay between requests in seconds (default: 1.2s for ~50/min)
    
    Returns:
        Summary of creation results with success/failure counts
    """
    try:
        client = get_slack_client()
        
        # Parse items data
        try:
            items = json.loads(items_data)
        except json.JSONDecodeError as e:
            return f"❌ Error parsing items_data JSON: {str(e)}"
        
        if not isinstance(items, list):
            return "❌ items_data must be a JSON array"
        
        successful = 0
        failed = 0
        results = []
        
        for i, item_data in enumerate(items, 1):
            try:
                title = item_data.get("title", f"Item {i}")
                
                # Create title field
                fields = [create_text_field(title_column_id, title)]
                
                # Add additional fields
                for field_def in item_data.get("fields", []):
                    column_id = field_def["column_id"]
                    field_type = field_def["type"]
                    value = field_def["value"]
                    
                    if field_type == "text":
                        fields.append(create_text_field(column_id, value))
                    elif field_type == "date":
                        fields.append(create_date_field(column_id, value))
                    elif field_type == "user":
                        user_ids = value if isinstance(value, list) else [value]
                        fields.append(create_user_field(column_id, user_ids))
                    elif field_type == "select":
                        option_ids = value if isinstance(value, list) else [value]
                        fields.append(create_select_field(column_id, option_ids))
                    elif field_type == "checkbox":
                        fields.append(create_checkbox_field(column_id, bool(value)))
                
                # Create the item
                result = await client.create_list_item(list_id, fields)
                item_id = result.get("item", {}).get("id", "Unknown")
                
                results.append(f"✅ Item {i}: {title} (ID: {item_id})")
                successful += 1
                
            except Exception as e:
                results.append(f"❌ Item {i}: Failed - {str(e)}")
                failed += 1
            
            # Rate limiting - wait between requests (except for the last item)
            if i < len(items):
                await asyncio.sleep(rate_limit_delay)
        
        summary = f"📊 Bulk creation completed!\n" \
                 f"Total items: {len(items)}\n" \
                 f"Successful: {successful}\n" \
                 f"Failed: {failed}\n" \
                 f"List ID: {list_id}\n\n" \
                 f"Results:\n" + "\n".join(results)
        
        return summary
        
    except SlackListsError as e:
        return f"❌ Slack Lists error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in create_multiple_list_items: {str(e)}")
        return f"❌ Unexpected error: {str(e)}"

@mcp.tool()
async def get_list_items(
    list_id: str,
    limit: int = 50,
    include_metadata: bool = True
) -> str:
    """Retrieve items from a Slack List.
    
    This tool fetches items from the specified Slack List with optional metadata.
    Use this to view current list contents, check item details, or prepare data for filtering.
    
    Args:
        list_id: The ID of the Slack List (format: F1234ABCD)
        limit: Maximum number of items to retrieve (default: 50, max: 100)
        include_metadata: Whether to include creation/update metadata (default: True)
    
    Returns:
        Formatted list of items with their field values and metadata
    """
    try:
        client = get_slack_client()
        
        # Limit the limit to reasonable bounds
        limit = min(max(1, limit), 100)
        
        # Get items from the list
        data = await client.get_list_items(list_id, limit=limit)
        items = data.get("items", [])
        
        if not items:
            return f"📝 No items found in list {list_id}"
        
        # Format items for display
        formatted_items = []
        
        for i, item in enumerate(items, 1):
            item_info = [f"Item {i}: {item.get('id', 'Unknown ID')}"]
            
            if include_metadata:
                created_date = datetime.fromtimestamp(item.get("date_created", 0)).isoformat()
                item_info.append(f"  Created: {created_date}")
                item_info.append(f"  Created by: {item.get('created_by', 'Unknown')}")
            
            # Add field values
            fields = item.get("fields", [])
            if fields:
                item_info.append("  Fields:")
                for field in fields:
                    column_id = field.get("column_id", "Unknown")
                    value = extract_field_value(item, column_id)
                    
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    
                    item_info.append(f"    {column_id}: {value}")
            
            formatted_items.append("\n".join(item_info))
        
        # Check if there are more items
        has_more = data.get("response_metadata", {}).get("next_cursor") is not None
        more_info = f"\n\n📄 Showing {len(items)} items" + (f" (more available)" if has_more else " (all items)")
        
        return f"📋 Items from list {list_id}:\n\n" + "\n\n".join(formatted_items) + more_info
        
    except SlackListsError as e:
        return f"❌ Slack Lists error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_list_items: {str(e)}")
        return f"❌ Unexpected error: {str(e)}"

@mcp.tool()
async def filter_list_items(
    list_id: str,
    filter_column_id: str,
    filter_value: str,
    filter_operator: str = "contains",
    max_items: int = 100
) -> str:
    """Filter and retrieve items from a Slack List based on field values.
    
    This tool allows you to search and filter list items by specific field values.
    Useful for finding items with specific status, assignee, priority, or any other field.
    
    Args:
        list_id: The ID of the Slack List (format: F1234ABCD)
        filter_column_id: Column ID to filter by (e.g., Col10000001)
        filter_value: Value to search for
        filter_operator: How to match the value. Options:
                        - "contains": Field contains the value (case-insensitive)
                        - "equals": Field exactly matches the value (case-insensitive)
                        - "not_equals": Field does not match the value
                        - "not_contains": Field does not contain the value
                        - "exists": Field has any non-empty value
                        - "not_exists": Field is empty or missing
        max_items: Maximum number of items to process (default: 100)
    
    Returns:
        Filtered list of items that match the criteria
    """
    try:
        client = get_slack_client()
        
        # Get all items (up to max_items)
        all_items = []
        cursor = None
        
        while len(all_items) < max_items:
            remaining = max_items - len(all_items)
            batch_size = min(100, remaining)
            
            data = await client.get_list_items(list_id, limit=batch_size, cursor=cursor)
            items = data.get("items", [])
            all_items.extend(items)
            
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor or not items:
                break
        
        if not all_items:
            return f"📝 No items found in list {list_id}"
        
        # Apply filter
        filtered_items = []
        
        for item in all_items:
            field_value = extract_field_value(item, filter_column_id)
            
            # Apply filter logic
            matches = False
            
            if filter_operator == "exists":
                matches = field_value is not None and field_value != ""
            elif filter_operator == "not_exists":
                matches = field_value is None or field_value == ""
            elif filter_operator == "equals":
                matches = str(field_value).lower() == str(filter_value).lower()
            elif filter_operator == "not_equals":
                matches = str(field_value).lower() != str(filter_value).lower()
            elif filter_operator == "contains":
                if field_value is not None:
                    matches = str(filter_value).lower() in str(field_value).lower()
            elif filter_operator == "not_contains":
                if field_value is None:
                    matches = True
                else:
                    matches = str(filter_value).lower() not in str(field_value).lower()
            
            if matches:
                filtered_items.append(item)
        
        if not filtered_items:
            return f"🔍 No items found matching filter:\n" \
                   f"Column: {filter_column_id}\n" \
                   f"Operator: {filter_operator}\n" \
                   f"Value: {filter_value}\n" \
                   f"Searched {len(all_items)} items in list {list_id}"
        
        # Format filtered items
        formatted_items = []
        
        for i, item in enumerate(filtered_items, 1):
            item_info = [f"Item {i}: {item.get('id', 'Unknown ID')}"]
            
            # Add field values
            fields = item.get("fields", [])
            if fields:
                item_info.append("  Fields:")
                for field in fields:
                    column_id = field.get("column_id", "Unknown")
                    value = extract_field_value(item, column_id)
                    
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    
                    # Highlight the filtered field
                    prefix = "  → " if column_id == filter_column_id else "    "
                    item_info.append(f"{prefix}{column_id}: {value}")
            
            formatted_items.append("\n".join(item_info))
        
        return f"🔍 Filtered items from list {list_id}:\n" \
               f"Filter: {filter_column_id} {filter_operator} '{filter_value}'\n" \
               f"Found: {len(filtered_items)} of {len(all_items)} items\n\n" + \
               "\n\n".join(formatted_items)
        
    except SlackListsError as e:
        return f"❌ Slack Lists error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in filter_list_items: {str(e)}")
        return f"❌ Unexpected error: {str(e)}"

@mcp.tool()
async def export_list_items(
    list_id: str,
    export_format: str = "json",
    filter_column_id: Optional[str] = None,
    filter_value: Optional[str] = None,
    filter_operator: str = "contains"
) -> str:
    """Export items from a Slack List to structured data format.
    
    This tool exports list items to JSON or CSV format, with optional filtering.
    Useful for backup, analysis, or integration with other systems.
    
    Args:
        list_id: The ID of the Slack List (format: F1234ABCD)
        export_format: Output format - "json" or "csv" (default: json)
        filter_column_id: Optional column ID to filter by
        filter_value: Value to filter for (required if filter_column_id is provided)
        filter_operator: Filter operator (contains, equals, not_equals, etc.)
    
    Returns:
        Exported data in the requested format, or error message
    """
    try:
        client = get_slack_client()
        
        # Get all items
        all_items = await client.get_all_list_items(list_id)
        
        if not all_items:
            return f"📝 No items found in list {list_id}"
        
        # Apply filter if specified
        items_to_export = all_items
        
        if filter_column_id and filter_value:
            filtered_items = []
            
            for item in all_items:
                field_value = extract_field_value(item, filter_column_id)
                
                matches = False
                if filter_operator == "exists":
                    matches = field_value is not None and field_value != ""
                elif filter_operator == "not_exists":
                    matches = field_value is None or field_value == ""
                elif filter_operator == "equals":
                    matches = str(field_value).lower() == str(filter_value).lower()
                elif filter_operator == "not_equals":
                    matches = str(field_value).lower() != str(filter_value).lower()
                elif filter_operator == "contains":
                    if field_value is not None:
                        matches = str(filter_value).lower() in str(field_value).lower()
                elif filter_operator == "not_contains":
                    if field_value is None:
                        matches = True
                    else:
                        matches = str(filter_value).lower() not in str(field_value).lower()
                
                if matches:
                    filtered_items.append(item)
            
            items_to_export = filtered_items
        
        if not items_to_export:
            return f"🔍 No items found matching the filter criteria"
        
        # Export based on format
        if export_format.lower() == "json":
            # Clean up items for JSON export
            export_data = []
            for item in items_to_export:
                clean_item = {
                    "id": item.get("id"),
                    "list_id": item.get("list_id"),
                    "created_date": datetime.fromtimestamp(item.get("date_created", 0)).isoformat(),
                    "created_by": item.get("created_by"),
                    "fields": {}
                }
                
                for field in item.get("fields", []):
                    column_id = field.get("column_id")
                    value = extract_field_value(item, column_id)
                    clean_item["fields"][column_id] = value
                
                export_data.append(clean_item)
            
            json_output = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            return f"📄 JSON Export from list {list_id}:\n" \
                   f"Items exported: {len(items_to_export)}\n" \
                   f"Filter applied: {bool(filter_column_id)}\n\n" \
                   f"```json\n{json_output}\n```"
        
        elif export_format.lower() == "csv":
            # Collect all unique column IDs
            all_columns = set()
            for item in items_to_export:
                for field in item.get("fields", []):
                    all_columns.add(field.get("column_id"))
            
            all_columns = sorted(list(all_columns))
            
            # Create CSV content
            csv_lines = []
            
            # Header
            headers = ["item_id", "created_date", "created_by"] + all_columns
            csv_lines.append(",".join(f'"{h}"' for h in headers))
            
            # Data rows
            for item in items_to_export:
                row = [
                    f'"{item.get("id", "")}"',
                    f'"{datetime.fromtimestamp(item.get("date_created", 0)).isoformat()}"',
                    f'"{item.get("created_by", "")}"'
                ]
                
                for col_id in all_columns:
                    value = extract_field_value(item, col_id)
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    row.append(f'"{str(value) if value is not None else ""}"')
                
                csv_lines.append(",".join(row))
            
            csv_output = "\n".join(csv_lines)
            
            return f"📊 CSV Export from list {list_id}:\n" \
                   f"Items exported: {len(items_to_export)}\n" \
                   f"Columns: {len(all_columns)}\n" \
                   f"Filter applied: {bool(filter_column_id)}\n\n" \
                   f"```csv\n{csv_output}\n```"
        
        else:
            return f"❌ Unsupported export format: {export_format}. Use 'json' or 'csv'."
        
    except SlackListsError as e:
        return f"❌ Slack Lists error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in export_list_items: {str(e)}")
        return f"❌ Unexpected error: {str(e)}"

# Server startup and configuration
if __name__ == "__main__":
    # Validate environment
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        logger.error("SLACK_BOT_TOKEN environment variable is required")
        exit(1)
    
    logger.info("Starting Slack Lists MCP Server...")
    logger.info("Available tools: create_list_item, create_multiple_list_items, get_list_items, filter_list_items, export_list_items")
    
    # Run the MCP server
    mcp.run(transport="stdio")

