"""
週間献立生成（毎週土曜日06:00実行）のエンドツーエンドテスト

実際のNotion/OpenAI/Slackに接続して、週間献立生成の全フローをテストします。

環境変数が必要:
    - NOTION_TOKEN
    - DB_ID_PROPOSED
    - DB_ID_RAW
    - DB_ID_STRUCTURED
    - OPENAI_API_KEY
    - SLACK_WEBHOOK_URL

実行方法:
    pytest tests/test_e2e_weekly_generation.py -v -s

-s オプションでログ出力を表示できます

注意: OpenAI APIへのAPIコール費用が発生します
"""

import logging
import os
from datetime import date

import pytest

from src.menu_generator import WeeklyMenuGenerator
from src.notion_client import NotionClientWrapper
from src.openai_client import OpenAIClientWrapper
from src.preprocessor import ActualDataPreprocessor
from src.slack_client import SlackClientWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.e2e
class TestWeeklyGenerationE2E:
    """週間献立生成のエンドツーエンドテスト"""

    @pytest.fixture
    def required_env_vars(self):
        """必要な環境変数を確認"""
        required = [
            "NOTION_TOKEN",
            "DB_ID_PROPOSED",
            "DB_ID_RAW",
            "DB_ID_STRUCTURED",
            "OPENAI_API_KEY",
            "SLACK_WEBHOOK_URL",
        ]

        missing = [var for var in required if not os.getenv(var)]

        if missing:
            pytest.skip(f"Missing environment variables: {', '.join(missing)}")

        return {var: os.getenv(var) for var in required}

    @pytest.fixture
    def clients(self, required_env_vars):
        """クライアントを初期化"""
        notion = NotionClientWrapper(token=required_env_vars["NOTION_TOKEN"])
        openai = OpenAIClientWrapper(api_key=required_env_vars["OPENAI_API_KEY"])
        slack = SlackClientWrapper(
            webhook_url=required_env_vars["SLACK_WEBHOOK_URL"]
        )
        return notion, openai, slack

    def test_all_connections(self, clients):
        """
        全サービスの接続テスト

        テスト内容:
        1. Notionへの接続確認
        2. OpenAI APIへの接続確認
        3. Slack Webhookへの接続確認
        """
        notion, openai, slack = clients

        logger.info("Testing all service connections...")

        # Notion接続テスト
        logger.info("  • Testing Notion connection...")
        assert notion.test_connection() is True, "Notion connection failed"
        logger.info("    ✓ Notion connection successful")

        # OpenAI接続テスト
        logger.info("  • Testing OpenAI connection...")
        assert openai.test_connection() is True, "OpenAI connection failed"
        logger.info("    ✓ OpenAI connection successful")

        # Slack接続テスト
        logger.info("  • Testing Slack connection...")
        assert slack.test_connection() is True, "Slack connection failed"
        logger.info("    ✓ Slack connection successful")

    def test_preprocessing_flow(self, clients):
        """
        実績データ構造化フロー（Step 1）

        テスト内容:
        1. Raw_Actual_Input から未処理レコードを取得
        2. OpenAI APIで構造化
        3. Structured_Actual_History に保存
        4. 処理済みフラグを更新
        """
        notion, openai, _ = clients

        logger.info("Testing preprocessing flow...")

        preprocessor = ActualDataPreprocessor(
            notion_client=notion,
            openai_client=openai,
        )

        result = preprocessor.process_all_unprocessed()

        logger.info(
            f"  Processed: {result.processed_count}, "
            f"Created: {result.created_count}"
        )

        if result.errors:
            for error in result.errors:
                logger.warning(f"  Warning: {error}")

        # 結果確認（エラーがないことを確認）
        assert all(
            "failed" not in err.lower() for err in result.errors
        ), f"Preprocessing errors: {result.errors}"

    def test_weekly_menu_generation(self, clients):
        """
        週間献立生成フロー（Step 2-3）

        テスト内容:
        1. 次週の既存予定を確認
        2. 空きを特定
        3. 過去の実績を取得
        4. OpenAI APIで献立を生成
        5. Notionに保存
        6. Slackに通知
        """
        notion, openai, slack = clients

        logger.info("Testing weekly menu generation flow...")

        generator = WeeklyMenuGenerator(
            notion_client=notion,
            openai_client=openai,
            slack_client=slack,
        )

        # テスト用の参照日を使用（実行日に依存しないように）
        test_date = date(2024, 1, 13)  # 土曜日

        result = generator.generate_for_next_week(reference_date=test_date)

        logger.info(
            f"  Generated: {result.generated_count}, "
            f"Skipped: {result.skipped}, "
            f"Skip reason: {result.skip_reason}"
        )

        if result.errors:
            for error in result.errors:
                logger.warning(f"  Error: {error}")

        # 結果確認
        assert not result.errors or all(
            "failed" not in err.lower() for err in result.errors
        ), f"Generation errors: {result.errors}"

    def test_full_weekly_flow_with_dry_run(self, clients):
        """
        完全な週間フロー（ドライラン）

        テスト内容:
        1. プリプロセッシング実行
        2. 献立生成実行
        3. エラーがないことを確認

        注意: 実際にNotionに保存とSlackに通知されます
        """
        notion, openai, slack = clients

        logger.info("Running full weekly flow with dry run...")

        # Step 1: プリプロセッシング
        logger.info("  [Step 1] Processing unprocessed records...")
        preprocessor = ActualDataPreprocessor(
            notion_client=notion,
            openai_client=openai,
        )
        preprocess_result = preprocessor.process_all_unprocessed()
        logger.info(
            f"    ✓ Processed: {preprocess_result.processed_count}, "
            f"Created: {preprocess_result.created_count}"
        )

        # Step 2-3: 献立生成
        logger.info("  [Step 2-3] Generating weekly menu...")
        generator = WeeklyMenuGenerator(
            notion_client=notion,
            openai_client=openai,
            slack_client=slack,
        )

        test_date = date(2024, 1, 13)  # 土曜日
        generation_result = generator.generate_for_next_week(reference_date=test_date)

        logger.info(
            f"    ✓ Generated: {generation_result.generated_count} items"
        )

        if generation_result.skipped:
            logger.info(f"    ℹ Skipped: {generation_result.skip_reason}")

        # 結果確認
        all_errors = preprocess_result.errors + generation_result.errors
        assert not all_errors or all(
            "failed" not in err.lower() for err in all_errors
        ), f"Flow errors: {all_errors}"

        logger.info("  ✓ Full flow completed successfully")


if __name__ == "__main__":
    # スクリプト直接実行時のテスト例
    import sys

    required = [
        "NOTION_TOKEN",
        "DB_ID_PROPOSED",
        "DB_ID_RAW",
        "DB_ID_STRUCTURED",
        "OPENAI_API_KEY",
        "SLACK_WEBHOOK_URL",
    ]

    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    # テスト実行
    pytest.main([__file__, "-v", "-s"])
