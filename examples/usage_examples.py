#!/usr/bin/env python3
"""
Usage Examples for Slack Lists MCP Server

This file demonstrates how to use the MCP server tools through an AI assistant
like Claude Desktop. These are example prompts and data formats you can use.

Note: This file is for reference only. The actual tools are called through
the MCP protocol by AI assistants, not directly by Python code.
"""

# Example 1: Create a single list item
create_single_item_example = {
    "tool": "create_list_item",
    "parameters": {
        "list_id": "F1234ABCD",
        "title": "Complete project documentation",
        "title_column_id": "Col10000000",
        "additional_fields": '[{"column_id": "Col10000001", "type": "date", "value": "2024-12-31"}, {"column_id": "Col10000002", "type": "select", "value": ["High"]}]'
    }
}

# Example 2: Create multiple list items
create_multiple_items_example = {
    "tool": "create_multiple_list_items", 
    "parameters": {
        "list_id": "F1234ABCD",
        "items_data": '''[
            {
                "title": "Design new feature",
                "fields": [
                    {"column_id": "Col10000001", "type": "date", "value": "2024-12-15"},
                    {"column_id": "Col10000002", "type": "select", "value": ["High"]},
                    {"column_id": "Col10000003", "type": "user", "value": ["U1234567"]}
                ]
            },
            {
                "title": "Fix bug #123",
                "fields": [
                    {"column_id": "Col10000001", "type": "date", "value": "2024-12-10"},
                    {"column_id": "Col10000002", "type": "select", "value": ["Medium"]},
                    {"column_id": "Col10000003", "type": "user", "value": ["U2345678"]}
                ]
            },
            {
                "title": "Write unit tests",
                "fields": [
                    {"column_id": "Col10000001", "type": "date", "value": "2024-12-20"},
                    {"column_id": "Col10000002", "type": "select", "value": ["Low"]},
                    {"column_id": "Col10000004", "type": "checkbox", "value": false}
                ]
            }
        ]''',
        "rate_limit_delay": 1.2
    }
}

# Example 3: Get list items
get_items_example = {
    "tool": "get_list_items",
    "parameters": {
        "list_id": "F1234ABCD",
        "limit": 25,
        "include_metadata": True
    }
}

# Example 4: Filter list items by status
filter_by_status_example = {
    "tool": "filter_list_items",
    "parameters": {
        "list_id": "F1234ABCD",
        "filter_column_id": "Col10000002",  # Status column
        "filter_value": "In Progress",
        "filter_operator": "equals",
        "max_items": 100
    }
}

# Example 5: Filter list items by assignee
filter_by_assignee_example = {
    "tool": "filter_list_items",
    "parameters": {
        "list_id": "F1234ABCD", 
        "filter_column_id": "Col10000003",  # Assignee column
        "filter_value": "U1234567",         # User ID
        "filter_operator": "contains",
        "max_items": 50
    }
}

# Example 6: Find items without assignee
filter_unassigned_example = {
    "tool": "filter_list_items",
    "parameters": {
        "list_id": "F1234ABCD",
        "filter_column_id": "Col10000003",  # Assignee column
        "filter_value": "",                 # Not used for exists/not_exists
        "filter_operator": "not_exists",
        "max_items": 100
    }
}

# Example 7: Export all items to JSON
export_json_example = {
    "tool": "export_list_items",
    "parameters": {
        "list_id": "F1234ABCD",
        "export_format": "json"
    }
}

# Example 8: Export filtered items to CSV
export_filtered_csv_example = {
    "tool": "export_list_items",
    "parameters": {
        "list_id": "F1234ABCD",
        "export_format": "csv",
        "filter_column_id": "Col10000002",  # Status column
        "filter_value": "Done",
        "filter_operator": "equals"
    }
}

# Common AI Assistant Prompts
ai_prompts = {
    "create_task": "Create a new task in my project list F1234ABCD with title 'Review code changes' and due date 2024-12-15",
    
    "bulk_create": "Add these 5 tasks to my list F1234ABCD: 1) Design mockups (due 12/10, high priority), 2) Write tests (due 12/15, medium), 3) Update docs (due 12/20, low), 4) Code review (due 12/12, high), 5) Deploy to staging (due 12/25, medium)",
    
    "view_tasks": "Show me all items in my project list F1234ABCD",
    
    "filter_high_priority": "Show me all high priority items from list F1234ABCD",
    
    "my_tasks": "Show me all tasks assigned to user U1234567 in list F1234ABCD",
    
    "completed_tasks": "Export all completed tasks from list F1234ABCD to CSV format",
    
    "overdue_items": "Find all items in list F1234ABCD that don't have a due date set",
    
    "status_report": "Give me a summary of all items in list F1234ABCD grouped by status"
}

# Field Type Reference
field_types_reference = {
    "text": {
        "description": "Rich text content",
        "example": {"column_id": "Col123", "type": "text", "value": "Task description"}
    },
    "date": {
        "description": "Date in YYYY-MM-DD format", 
        "example": {"column_id": "Col123", "type": "date", "value": "2024-12-31"}
    },
    "user": {
        "description": "Slack user ID(s)",
        "example": {"column_id": "Col123", "type": "user", "value": ["U1234567", "U2345678"]}
    },
    "select": {
        "description": "Select option ID(s)",
        "example": {"column_id": "Col123", "type": "select", "value": ["OptionHigh123"]}
    },
    "checkbox": {
        "description": "Boolean true/false",
        "example": {"column_id": "Col123", "type": "checkbox", "value": True}
    },
    "number": {
        "description": "Numeric value",
        "example": {"column_id": "Col123", "type": "number", "value": 42}
    },
    "email": {
        "description": "Email address",
        "example": {"column_id": "Col123", "type": "email", "value": "user@example.com"}
    },
    "phone": {
        "description": "Phone number",
        "example": {"column_id": "Col123", "type": "phone", "value": "+1-555-123-4567"}
    }
}

# Filter Operators Reference
filter_operators_reference = {
    "contains": "Field contains the value (case-insensitive)",
    "equals": "Field exactly matches the value (case-insensitive)", 
    "not_equals": "Field does not match the value",
    "not_contains": "Field does not contain the value",
    "exists": "Field has any non-empty value",
    "not_exists": "Field is empty or missing"
}

if __name__ == "__main__":
    print("Slack Lists MCP Server - Usage Examples")
    print("=" * 50)
    print()
    print("This file contains example usage patterns for the MCP server.")
    print("Use these examples as reference when working with AI assistants.")
    print()
    print("Available Tools:")
    print("- create_list_item: Create a single item")
    print("- create_multiple_list_items: Create multiple items with rate limiting")
    print("- get_list_items: Retrieve items from a list")
    print("- filter_list_items: Filter items by field values")
    print("- export_list_items: Export items to JSON or CSV")
    print()
    print("See the examples above for detailed usage patterns.")

