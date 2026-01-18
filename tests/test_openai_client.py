"""
OpenAIクライアントのテスト
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.openai_client import OpenAIClientWrapper


class TestStructureRawInput:
    """実績データ構造化のテスト"""

    def test_structure_raw_input_single_dish(self):
        """単一の料理を構造化"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"dishes": [{"dish_name": "キムチ鍋", "category": "主菜"}]}'
                )
            )
        ]

        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response
            client.model = "gpt-4o"

            result = client.structure_raw_input("キムチ鍋", date(2024, 1, 15))

            assert len(result) == 1
            assert result[0].dish_name == "キムチ鍋"
            assert result[0].category == "主菜"

    def test_structure_raw_input_multiple_dishes(self):
        """複数の料理を構造化"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"dishes": [{"dish_name": "キムチ鍋", "category": "主菜"}, {"dish_name": "しめのラーメン", "category": "その他"}]}'
                )
            )
        ]

        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response
            client.model = "gpt-4o"

            result = client.structure_raw_input(
                "キムチ鍋、しめのラーメン", date(2024, 1, 15)
            )

            assert len(result) == 2
            assert result[0].dish_name == "キムチ鍋"
            assert result[1].dish_name == "しめのラーメン"

    def test_structure_raw_input_invalid_category(self):
        """無効なカテゴリは「その他」にフォールバック"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"dishes": [{"dish_name": "ケーキ", "category": "デザート"}]}'
                )
            )
        ]

        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response
            client.model = "gpt-4o"

            result = client.structure_raw_input("ケーキ", date(2024, 1, 15))

            assert len(result) == 1
            assert result[0].category == "その他"

    def test_structure_raw_input_empty_response(self):
        """空のレスポンスの場合"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response
            client.model = "gpt-4o"

            result = client.structure_raw_input("何か", date(2024, 1, 15))

            assert result == []


class TestGenerateWeeklyMenu:
    """週間献立生成のテスト"""

    def test_generate_weekly_menu_success(self):
        """正常な献立生成"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""{
                        "menu": [
                            {"date": "2024-01-15", "dish_name": "鶏の唐揚げ", "category": "主菜", "shopping_list": "鶏もも肉, 片栗粉"},
                            {"date": "2024-01-15", "dish_name": "ほうれん草のお浸し", "category": "副菜", "shopping_list": "ほうれん草"}
                        ]
                    }"""
                )
            )
        ]

        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()
            client.client = MagicMock()
            client.client.chat.completions.create.return_value = mock_response
            client.model = "gpt-4o"

            result = client.generate_weekly_menu(
                dates_to_fill=[date(2024, 1, 15)],
                existing_plans=[],
                recent_history=[],
            )

            assert len(result) == 2
            assert result[0].dish_name == "鶏の唐揚げ"
            assert result[0].date == date(2024, 1, 15)
            assert result[0].category == "主菜"
            assert "鶏もも肉" in result[0].shopping_list

    def test_generate_weekly_menu_no_dates(self):
        """生成対象日がない場合"""
        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()
            client.client = MagicMock()
            client.model = "gpt-4o"

            result = client.generate_weekly_menu(
                dates_to_fill=[],
                existing_plans=[],
                recent_history=[],
            )

            assert result == []


class TestFormatMethods:
    """フォーマットヘルパーメソッドのテスト"""

    def test_format_existing_plans(self):
        """既存予定のフォーマット"""
        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()

            plans = [
                {
                    "date": "2024-01-15",
                    "dish_name": "外食",
                    "category": "その他",
                    "status": "外食・予定あり",
                }
            ]

            result = client._format_existing_plans(plans)

            assert "2024-01-15" in result
            assert "外食" in result
            assert "外食・予定あり" in result

    def test_format_existing_plans_empty(self):
        """空の既存予定"""
        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()

            result = client._format_existing_plans([])

            assert result == ""

    def test_format_history(self):
        """履歴のフォーマット"""
        with patch.object(OpenAIClientWrapper, "__init__", lambda x, **kwargs: None):
            client = OpenAIClientWrapper()

            history = [
                {"date": "2024-01-10", "dish_name": "カレーライス", "category": "主菜"}
            ]

            result = client._format_history(history)

            assert "2024-01-10" in result
            assert "カレーライス" in result
            assert "主菜" in result
