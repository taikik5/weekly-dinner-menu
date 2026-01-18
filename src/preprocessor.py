"""
実績データ構造化プリプロセッサ

Raw_Actual_Input テーブルの自由記述を
Structured_Actual_History テーブルに構造化して保存します。
"""

import logging
from dataclasses import dataclass

from src.notion_client import (
    NotionClientWrapper,
    RawActualInput,
    StructuredActualHistory,
)
from src.openai_client import OpenAIClientWrapper

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    """プリプロセス結果"""

    processed_count: int  # 処理したレコード数
    created_count: int  # 作成した構造化レコード数
    errors: list[str]  # エラーメッセージリスト


class ActualDataPreprocessor:
    """
    実績データの構造化を行うプリプロセッサ。

    Raw_Actual_Input から未処理のレコードを取得し、
    OpenAI APIで構造化した後、Structured_Actual_History に保存します。
    """

    def __init__(
        self,
        notion_client: NotionClientWrapper | None = None,
        openai_client: OpenAIClientWrapper | None = None,
    ):
        """
        プリプロセッサを初期化します。

        Args:
            notion_client: Notionクライアント（省略時は新規作成）
            openai_client: OpenAIクライアント（省略時は新規作成）
        """
        self.notion = notion_client or NotionClientWrapper()
        self.openai = openai_client or OpenAIClientWrapper()

    def process_all_unprocessed(self) -> PreprocessingResult:
        """
        全ての未処理レコードを構造化して保存します。

        Returns:
            処理結果
        """
        errors: list[str] = []
        processed_count = 0
        created_count = 0

        # 未処理のレコードを取得
        try:
            unprocessed = self.notion.get_unprocessed_raw_inputs()
        except Exception as e:
            logger.error(f"Failed to fetch unprocessed records: {e}")
            return PreprocessingResult(
                processed_count=0,
                created_count=0,
                errors=[f"Notionからのデータ取得に失敗: {e}"],
            )

        if not unprocessed:
            logger.info("No unprocessed records found")
            return PreprocessingResult(
                processed_count=0,
                created_count=0,
                errors=[],
            )

        logger.info(f"Found {len(unprocessed)} unprocessed records")

        # 各レコードを処理
        for record in unprocessed:
            result = self._process_single_record(record)
            if result.success:
                processed_count += 1
                created_count += result.created_items
            else:
                errors.append(result.error_message)

        return PreprocessingResult(
            processed_count=processed_count,
            created_count=created_count,
            errors=errors,
        )

    def _process_single_record(self, record: RawActualInput) -> "_SingleProcessResult":
        """
        単一のレコードを処理します。

        Args:
            record: 処理対象のレコード

        Returns:
            処理結果
        """
        if not record.id:
            return _SingleProcessResult(
                success=False,
                created_items=0,
                error_message="Record ID is missing",
            )

        if not record.food_eaten.strip():
            # 空の記述は処理済みにしてスキップ
            try:
                self.notion.mark_raw_input_as_processed(record.id)
                logger.info(f"Skipped empty record: {record.id}")
                return _SingleProcessResult(success=True, created_items=0)
            except Exception as e:
                return _SingleProcessResult(
                    success=False,
                    created_items=0,
                    error_message=f"Failed to mark empty record as processed: {e}",
                )

        # OpenAI APIで構造化
        try:
            structured_dishes = self.openai.structure_raw_input(
                raw_text=record.food_eaten,
                eaten_date=record.date,
            )
        except Exception as e:
            logger.error(f"OpenAI API error for record {record.id}: {e}")
            return _SingleProcessResult(
                success=False,
                created_items=0,
                error_message=f"構造化に失敗 (日付: {record.date}): {e}",
            )

        if not structured_dishes:
            # 構造化結果が空でも処理済みにする
            try:
                self.notion.mark_raw_input_as_processed(record.id)
                logger.warning(
                    f"No dishes extracted from record {record.id}: {record.food_eaten}"
                )
                return _SingleProcessResult(success=True, created_items=0)
            except Exception as e:
                return _SingleProcessResult(
                    success=False,
                    created_items=0,
                    error_message=f"Failed to mark record as processed: {e}",
                )

        # Structured_Actual_History に保存
        created_items = 0
        for dish in structured_dishes:
            try:
                history = StructuredActualHistory(
                    id=None,
                    dish_name=dish.dish_name,
                    date=record.date,
                    category=dish.category,
                )
                self.notion.create_structured_history(history)
                created_items += 1
                logger.info(
                    f"Created structured history: {dish.dish_name} ({dish.category})"
                )
            except Exception as e:
                logger.error(f"Failed to create structured history: {e}")
                # 一部失敗しても続行

        # 元のレコードを処理済みにマーク
        try:
            self.notion.mark_raw_input_as_processed(record.id)
            logger.info(f"Marked record as processed: {record.id}")
        except Exception as e:
            return _SingleProcessResult(
                success=False,
                created_items=created_items,
                error_message=f"Failed to mark record as processed: {e}",
            )

        return _SingleProcessResult(
            success=True,
            created_items=created_items,
        )


@dataclass
class _SingleProcessResult:
    """単一レコードの処理結果"""

    success: bool
    created_items: int = 0
    error_message: str = ""
