#!/usr/bin/env python3
"""
Basic tests for Slack Lists MCP Server

These tests validate the server functionality without requiring actual Slack API calls.
For full integration testing, you'll need valid Slack credentials and list IDs.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, AsyncMock
import sys
import asyncio

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from slack_lists_server import (
    SlackListsClient, 
    SlackListsError,
    create_text_field,
    create_date_field,
    create_user_field,
    create_select_field,
    create_checkbox_field,
    extract_field_value
)

class TestFieldHelpers:
    """Test field creation helper functions"""
    
    def test_create_text_field(self):
        field = create_text_field("Col123", "Test text")
        assert field["column_id"] == "Col123"
        assert field["rich_text"][0]["elements"][0]["elements"][0]["text"] == "Test text"
    
    def test_create_date_field(self):
        field = create_date_field("Col123", "2024-12-31")
        assert field["column_id"] == "Col123"
        assert field["date"] == ["2024-12-31"]
    
    def test_create_user_field(self):
        field = create_user_field("Col123", ["U1234567"])
        assert field["column_id"] == "Col123"
        assert field["user"] == ["U1234567"]
    
    def test_create_select_field(self):
        field = create_select_field("Col123", ["Option1"])
        assert field["column_id"] == "Col123"
        assert field["select"] == ["Option1"]
    
    def test_create_checkbox_field(self):
        field = create_checkbox_field("Col123", True)
        assert field["column_id"] == "Col123"
        assert field["checkbox"] is True

class TestFieldExtraction:
    """Test field value extraction from items"""
    
    def test_extract_text_field(self):
        item = {
            "fields": [
                {"column_id": "Col123", "text": "Test value"}
            ]
        }
        value = extract_field_value(item, "Col123")
        assert value == "Test value"
    
    def test_extract_date_field(self):
        item = {
            "fields": [
                {"column_id": "Col123", "date": ["2024-12-31"]}
            ]
        }
        value = extract_field_value(item, "Col123")
        assert value == "2024-12-31"
    
    def test_extract_user_field(self):
        item = {
            "fields": [
                {"column_id": "Col123", "user": ["U1234567", "U2345678"]}
            ]
        }
        value = extract_field_value(item, "Col123")
        assert value == ["U1234567", "U2345678"]
    
    def test_extract_checkbox_field(self):
        item = {
            "fields": [
                {"column_id": "Col123", "checkbox": True}
            ]
        }
        value = extract_field_value(item, "Col123")
        assert value is True
    
    def test_extract_missing_field(self):
        item = {
            "fields": [
                {"column_id": "Col456", "text": "Other value"}
            ]
        }
        value = extract_field_value(item, "Col123")
        assert value is None

class TestSlackListsClient:
    """Test Slack Lists client functionality"""
    
    def test_client_initialization(self):
        client = SlackListsClient("test-token")
        assert client.token == "test-token"
        assert "Bearer test-token" in client.headers["Authorization"]
    
    @pytest.mark.asyncio
    async def test_make_request_success(self):
        client = SlackListsClient("test-token")
        
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True, "data": "test"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client._make_request("GET", "test.endpoint")
            assert result == {"ok": True, "data": "test"}
    
    @pytest.mark.asyncio
    async def test_make_request_slack_error(self):
        client = SlackListsClient("test-token")
        
        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "invalid_auth"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(SlackListsError) as exc_info:
                await client._make_request("GET", "test.endpoint")
            
            assert "invalid_auth" in str(exc_info.value)

class TestEnvironmentValidation:
    """Test environment variable validation"""
    
    def test_missing_token_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch('slack_lists_server.slack_client', None):
                from slack_lists_server import get_slack_client
                
                with pytest.raises(SlackListsError) as exc_info:
                    get_slack_client()
                
                assert "SLACK_BOT_TOKEN" in str(exc_info.value)
    
    def test_valid_token_creates_client(self):
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "test-token"}):
            with patch('slack_lists_server.slack_client', None):
                from slack_lists_server import get_slack_client
                
                client = get_slack_client()
                assert client.token == "test-token"

class TestJSONParsing:
    """Test JSON parsing in tool functions"""
    
    def test_valid_json_parsing(self):
        json_str = '[{"column_id": "Col123", "type": "text", "value": "test"}]'
        parsed = json.loads(json_str)
        assert len(parsed) == 1
        assert parsed[0]["column_id"] == "Col123"
    
    def test_invalid_json_handling(self):
        json_str = '{"invalid": json}'
        with pytest.raises(json.JSONDecodeError):
            json.loads(json_str)

# Integration test helpers (require actual Slack setup)
class TestIntegrationHelpers:
    """Helper functions for integration testing with real Slack API"""
    
    @staticmethod
    def requires_slack_setup():
        """Decorator to skip tests that require Slack setup"""
        return pytest.mark.skipif(
            not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("TEST_LIST_ID"),
            reason="Requires SLACK_BOT_TOKEN and TEST_LIST_ID environment variables"
        )
    
    @staticmethod
    def get_test_config():
        """Get test configuration from environment"""
        return {
            "token": os.getenv("SLACK_BOT_TOKEN"),
            "list_id": os.getenv("TEST_LIST_ID"),
            "title_column_id": os.getenv("TEST_TITLE_COLUMN_ID", "Col10000000")
        }

# Example integration test (requires setup)
class TestIntegration:
    """Integration tests with real Slack API (requires setup)"""
    
    @TestIntegrationHelpers.requires_slack_setup()
    @pytest.mark.asyncio
    async def test_create_and_retrieve_item(self):
        """Test creating and retrieving an item (requires real Slack setup)"""
        config = TestIntegrationHelpers.get_test_config()
        client = SlackListsClient(config["token"])
        
        # Create a test item
        fields = [create_text_field(config["title_column_id"], "Test Item")]
        result = await client.create_list_item(config["list_id"], fields)
        
        assert result["ok"] is True
        item_id = result["item"]["id"]
        
        # Retrieve items to verify creation
        items_result = await client.get_list_items(config["list_id"], limit=10)
        assert items_result["ok"] is True
        
        # Find our created item
        created_item = None
        for item in items_result["items"]:
            if item["id"] == item_id:
                created_item = item
                break
        
        assert created_item is not None
        title_value = extract_field_value(created_item, config["title_column_id"])
        assert "Test Item" in str(title_value)

if __name__ == "__main__":
    print("Running Slack Lists MCP Server Tests")
    print("=" * 40)
    
    # Run basic tests
    pytest.main([__file__, "-v"])
    
    print("\nTo run integration tests, set these environment variables:")
    print("- SLACK_BOT_TOKEN: Your Slack bot token")
    print("- TEST_LIST_ID: A test list ID (e.g., F1234ABCD)")
    print("- TEST_TITLE_COLUMN_ID: Title column ID (optional, defaults to Col10000000)")
    print("\nThen run: pytest tests/test_server.py -v")

