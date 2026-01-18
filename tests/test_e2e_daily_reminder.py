"""
日次リマインダー（毎日19:00実行）のエンドツーエンドテスト

実際のNotionとSlackに接続して、日次リマインダーの全フローをテストします。

環境変数が必要:
    - NOTION_TOKEN
    - DB_ID_PROPOSED
    - SLACK_WEBHOOK_URL

実行方法:
    pytest tests/test_e2e_daily_reminder.py -v -s

-s オプションでログ出力を表示できます
"""

import logging
import os
from datetime import date

import pytest

from src.daily_reminder import DailyReminderSender
from src.notion_client import NotionClientWrapper
from src.slack_client import SlackClientWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.e2e
class TestDailyReminderE2E:
    """日次リマインダーのエンドツーエンドテスト"""

    @pytest.fixture
    def required_env_vars(self):
        """必要な環境変数を確認"""
        required = [
            "NOTION_TOKEN",
            "DB_ID_PROPOSED",
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
        slack = SlackClientWrapper(
            webhook_url=required_env_vars["SLACK_WEBHOOK_URL"]
        )
        return notion, slack

    def test_send_daily_reminder_today(self, clients):
        """
        今日の献立でリマインダーを送信

        テスト内容:
        1. 今日の献立をNotionから取得
        2. Slackにリマインダーを送信
        3. 送信成功を確認
        """
        notion, slack = clients
        target_date = date.today()

        logger.info(f"Testing daily reminder for {target_date.isoformat()}")

        # リマインダー送信
        sender = DailyReminderSender(
            notion_client=notion,
            slack_client=slack,
        )

        result = sender.send_reminder(target_date)

        logger.info(
            f"Reminder sent: {result.sent}, "
            f"Menu items: {result.menu_count}, "
            f"Error: {result.error}"
        )

        # 結果確認
        assert result.sent is True, f"Failed to send reminder: {result.error}"
        assert result.menu_count >= 0  # 予定がないこともある

    def test_send_daily_reminder_specific_date(self, clients):
        """
        特定の日付でリマインダーを送信

        テスト内容:
        1. 指定日付の献立をNotionから取得
        2. Slackにリマインダーを送信
        3. 送信成功を確認
        """
        notion, slack = clients

        # テスト用: 1月15日を指定
        test_date = date(2024, 1, 15)

        logger.info(f"Testing daily reminder for {test_date.isoformat()}")

        sender = DailyReminderSender(
            notion_client=notion,
            slack_client=slack,
        )

        result = sender.send_reminder(test_date)

        logger.info(
            f"Reminder sent: {result.sent}, "
            f"Menu items: {result.menu_count}, "
            f"Error: {result.error}"
        )

        # 結果確認
        assert result.sent is True, f"Failed to send reminder: {result.error}"
        assert result.menu_count >= 0

    def test_slack_and_notion_connections(self, clients):
        """
        Slackとnotionの接続テスト

        実際のAPIへの接続を確認
        """
        notion, slack = clients

        # Notion接続テスト
        logger.info("Testing Notion connection...")
        assert notion.test_connection() is True, "Notion connection failed"
        logger.info("✓ Notion connection successful")

        # Slack接続テスト
        logger.info("Testing Slack connection...")
        assert slack.test_connection() is True, "Slack connection failed"
        logger.info("✓ Slack connection successful")


if __name__ == "__main__":
    # スクリプト直接実行時のテスト例
    import sys

    if not os.getenv("NOTION_TOKEN"):
        print("Error: NOTION_TOKEN environment variable is not set")
        sys.exit(1)

    if not os.getenv("DB_ID_PROPOSED"):
        print("Error: DB_ID_PROPOSED environment variable is not set")
        sys.exit(1)

    if not os.getenv("SLACK_WEBHOOK_URL"):
        print("Error: SLACK_WEBHOOK_URL environment variable is not set")
        sys.exit(1)

    # テスト実行
    pytest.main([__file__, "-v", "-s"])
