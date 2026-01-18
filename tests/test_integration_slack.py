"""
Slack通知の統合テスト

実際のSlack Webhookに通知を送信してテストします。
環境変数 SLACK_WEBHOOK_URL が必要です。

実行方法:
    pytest tests/test_integration_slack.py -v

または環境変数を指定して実行:
    SLACK_WEBHOOK_URL="https://hooks.slack.com/..." pytest tests/test_integration_slack.py -v
"""

import os
from datetime import date

import pytest

from src.slack_client import SlackClientWrapper


@pytest.mark.integration
class TestSlackIntegration:
    """Slack統合テスト"""

    @pytest.fixture
    def slack_client(self):
        """Slackクライアントを初期化"""
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            pytest.skip("SLACK_WEBHOOK_URL is not set")
        return SlackClientWrapper(webhook_url=webhook_url)

    def test_send_message_basic(self, slack_client):
        """基本的なメッセージ送信"""
        result = slack_client.send_message("🔧 テストメッセージです")
        assert result is True

    def test_send_weekly_menu_notification(self, slack_client):
        """週間献立通知の送信"""
        menu_items = [
            {
                "date": "2024-01-15",
                "dish_name": "鶏の唐揚げ",
                "category": "主菜",
                "status": "確定",
                "shopping_list": "鶏もも肉, 片栗粉, 醤油",
            },
            {
                "date": "2024-01-15",
                "dish_name": "ほうれん草のお浸し",
                "category": "副菜",
                "status": "提案",
                "shopping_list": "ほうれん草, 醤油, みりん",
            },
            {
                "date": "2024-01-15",
                "dish_name": "味噌汁",
                "category": "汁物",
                "status": "提案",
                "shopping_list": "豆腐, わかめ, 味噌",
            },
        ]

        result = slack_client.send_weekly_menu_notification(
            menu_items=menu_items,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 21),
            notion_url="https://www.notion.so/test",
        )

        assert result is True

    def test_send_daily_reminder(self, slack_client):
        """日次リマインダーの送信"""
        today_menu = [
            {
                "dish_name": "鶏の唐揚げ",
                "category": "主菜",
                "status": "確定",
            },
            {
                "dish_name": "ほうれん草のお浸し",
                "category": "副菜",
                "status": "提案",
            },
        ]

        result = slack_client.send_daily_reminder(
            today_date=date(2024, 1, 15),
            today_menu=today_menu,
            notion_url="https://www.notion.so/test",
        )

        assert result is True

    def test_send_error_notification(self, slack_client):
        """エラー通知の送信"""
        result = slack_client.send_error_notification(
            error_message="テスト用のエラーメッセージ",
            context="システムテスト",
        )

        assert result is True

    def test_send_skip_notification(self, slack_client):
        """スキップ通知の送信"""
        result = slack_client.send_skip_notification(
            reason="テスト用: 全ての日に予定が入っています",
            week_range="2024-01-15 - 2024-01-21",
        )

        assert result is True

    def test_connection(self, slack_client):
        """Slack接続テスト"""
        result = slack_client.test_connection()
        assert result is True
