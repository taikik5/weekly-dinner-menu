"""
プリプロセッサのテスト
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.notion_client import RawActualInput
from src.openai_client import StructuredDish
from src.preprocessor import ActualDataPreprocessor


class TestProcessAllUnprocessed:
    """未処理レコード処理のテスト"""

    def test_process_no_records(self):
        """処理対象レコードがない場合"""
        mock_notion = MagicMock()
        mock_notion.get_unprocessed_raw_inputs.return_value = []

        mock_openai = MagicMock()

        preprocessor = ActualDataPreprocessor(
            notion_client=mock_notion, openai_client=mock_openai
        )

        result = preprocessor.process_all_unprocessed()

        assert result.processed_count == 0
        assert result.created_count == 0
        assert len(result.errors) == 0

    def test_process_single_record(self):
        """単一レコードの処理"""
        mock_notion = MagicMock()
        mock_notion.get_unprocessed_raw_inputs.return_value = [
            RawActualInput(
                id="raw-1",
                date=date(2024, 1, 15),
                food_eaten="キムチ鍋",
                is_processed=False,
            )
        ]
        mock_notion.create_structured_history.return_value = "history-1"

        mock_openai = MagicMock()
        mock_openai.structure_raw_input.return_value = [
            StructuredDish(dish_name="キムチ鍋", category="主菜")
        ]

        preprocessor = ActualDataPreprocessor(
            notion_client=mock_notion, openai_client=mock_openai
        )

        result = preprocessor.process_all_unprocessed()

        assert result.processed_count == 1
        assert result.created_count == 1
        assert len(result.errors) == 0
        mock_notion.mark_raw_input_as_processed.assert_called_once_with("raw-1")

    def test_process_empty_food_eaten(self):
        """空の食べたもの記述"""
        mock_notion = MagicMock()
        mock_notion.get_unprocessed_raw_inputs.return_value = [
            RawActualInput(
                id="raw-1",
                date=date(2024, 1, 15),
                food_eaten="   ",  # 空白のみ
                is_processed=False,
            )
        ]

        mock_openai = MagicMock()

        preprocessor = ActualDataPreprocessor(
            notion_client=mock_notion, openai_client=mock_openai
        )

        result = preprocessor.process_all_unprocessed()

        assert result.processed_count == 1
        assert result.created_count == 0
        mock_openai.structure_raw_input.assert_not_called()
        mock_notion.mark_raw_input_as_processed.assert_called_once_with("raw-1")

    def test_process_multiple_dishes_from_single_record(self):
        """1レコードから複数の料理を抽出"""
        mock_notion = MagicMock()
        mock_notion.get_unprocessed_raw_inputs.return_value = [
            RawActualInput(
                id="raw-1",
                date=date(2024, 1, 15),
                food_eaten="キムチ鍋、しめのラーメン",
                is_processed=False,
            )
        ]
        mock_notion.create_structured_history.return_value = "history-x"

        mock_openai = MagicMock()
        mock_openai.structure_raw_input.return_value = [
            StructuredDish(dish_name="キムチ鍋", category="主菜"),
            StructuredDish(dish_name="しめのラーメン", category="その他"),
        ]

        preprocessor = ActualDataPreprocessor(
            notion_client=mock_notion, openai_client=mock_openai
        )

        result = preprocessor.process_all_unprocessed()

        assert result.processed_count == 1
        assert result.created_count == 2
        assert mock_notion.create_structured_history.call_count == 2

    def test_process_openai_returns_empty(self):
        """OpenAIが空の結果を返す場合"""
        mock_notion = MagicMock()
        mock_notion.get_unprocessed_raw_inputs.return_value = [
            RawActualInput(
                id="raw-1",
                date=date(2024, 1, 15),
                food_eaten="よくわからないもの",
                is_processed=False,
            )
        ]

        mock_openai = MagicMock()
        mock_openai.structure_raw_input.return_value = []

        preprocessor = ActualDataPreprocessor(
            notion_client=mock_notion, openai_client=mock_openai
        )

        result = preprocessor.process_all_unprocessed()

        assert result.processed_count == 1
        assert result.created_count == 0
        mock_notion.mark_raw_input_as_processed.assert_called_once_with("raw-1")
