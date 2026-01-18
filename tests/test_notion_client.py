"""
Notionクライアントのテスト
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.notion_client import (
    NotionClientWrapper,
    ProposedDish,
    RawActualInput,
    StructuredActualHistory,
)


class TestProposedDishParsing:
    """ProposedDishのパース処理テスト"""

    def test_parse_proposed_dish_complete(self):
        """全フィールドが揃っている場合のパース"""
        page = {
            "id": "page-123",
            "properties": {
                "料理名": {"title": [{"plain_text": "鶏の唐揚げ"}]},
                "日付": {"date": {"start": "2024-01-15"}},
                "区分": {"select": {"name": "主菜"}},
                "ステータス": {"select": {"name": "確定"}},
                "買い物リスト": {"rich_text": [{"plain_text": "鶏もも肉, 片栗粉"}]},
            },
        }

        with patch.object(NotionClientWrapper, "__init__", lambda x, y=None: None):
            client = NotionClientWrapper()
            client.client = MagicMock()

            dish = client._parse_proposed_dish(page)

            assert dish.id == "page-123"
            assert dish.dish_name == "鶏の唐揚げ"
            assert dish.date == date(2024, 1, 15)
            assert dish.category == "主菜"
            assert dish.status == "確定"
            assert dish.shopping_list == "鶏もも肉, 片栗粉"

    def test_parse_proposed_dish_empty_fields(self):
        """フィールドが空の場合のパース"""
        page = {
            "id": "page-456",
            "properties": {
                "料理名": {"title": []},
                "日付": {"date": None},
                "区分": {"select": None},
                "ステータス": {"select": None},
                "買い物リスト": {"rich_text": []},
            },
        }

        with patch.object(NotionClientWrapper, "__init__", lambda x, y=None: None):
            client = NotionClientWrapper()
            client.client = MagicMock()

            dish = client._parse_proposed_dish(page)

            assert dish.id == "page-456"
            assert dish.dish_name == ""
            assert dish.category == "その他"
            assert dish.status == "提案"
            assert dish.shopping_list == ""


class TestRawInputParsing:
    """RawActualInputのパース処理テスト"""

    def test_parse_raw_input_complete(self):
        """全フィールドが揃っている場合のパース"""
        page = {
            "id": "raw-123",
            "properties": {
                "食べたもの": {"title": [{"plain_text": "キムチ鍋、しめのラーメン"}]},
                "日付": {"date": {"start": "2024-01-15"}},
                "処理済み": {"checkbox": False},
            },
        }

        with patch.object(NotionClientWrapper, "__init__", lambda x, y=None: None):
            client = NotionClientWrapper()
            client.client = MagicMock()

            raw = client._parse_raw_input(page)

            assert raw.id == "raw-123"
            assert raw.food_eaten == "キムチ鍋、しめのラーメン"
            assert raw.date == date(2024, 1, 15)
            assert raw.is_processed is False


class TestStructuredHistoryParsing:
    """StructuredActualHistoryのパース処理テスト"""

    def test_parse_structured_history_complete(self):
        """全フィールドが揃っている場合のパース"""
        page = {
            "id": "history-123",
            "properties": {
                "料理名": {"title": [{"plain_text": "キムチ鍋"}]},
                "日付": {"date": {"start": "2024-01-15"}},
                "区分": {"select": {"name": "主菜"}},
            },
        }

        with patch.object(NotionClientWrapper, "__init__", lambda x, y=None: None):
            client = NotionClientWrapper()
            client.client = MagicMock()

            history = client._parse_structured_history(page)

            assert history.id == "history-123"
            assert history.dish_name == "キムチ鍋"
            assert history.date == date(2024, 1, 15)
            assert history.category == "主菜"


class TestDatabaseUrl:
    """データベースURL生成のテスト"""

    def test_get_database_url(self):
        """ハイフンなしのIDからURLを生成"""
        with patch.object(NotionClientWrapper, "__init__", lambda x, y=None: None):
            client = NotionClientWrapper()
            client.client = MagicMock()

            url = client.get_database_url("abc123def456")
            assert url == "https://www.notion.so/abc123def456"

    def test_get_database_url_with_hyphens(self):
        """ハイフン付きIDからURLを生成"""
        with patch.object(NotionClientWrapper, "__init__", lambda x, y=None: None):
            client = NotionClientWrapper()
            client.client = MagicMock()

            url = client.get_database_url("abc-123-def-456")
            assert url == "https://www.notion.so/abc123def456"
