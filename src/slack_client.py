"""
Slack Webhook クライアント

Slackへの通知を担当します。
"""

from datetime import date

import requests

from config.settings import SLACK_WEBHOOK_URL


class SlackClientWrapper:
    """
    Slack Webhookを使用した通知クライアント。
    """

    def __init__(self, webhook_url: str | None = None):
        """
        クライアントを初期化します。

        Args:
            webhook_url: Slack Webhook URL。省略時は環境変数から取得。
        """
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("Slack webhook URL is required")

    def send_message(self, text: str, blocks: list[dict] | None = None) -> bool:
        """
        Slackにメッセージを送信します。

        Args:
            text: フォールバック用テキスト
            blocks: Block Kit形式のメッセージ（オプション）

        Returns:
            送信成功ならTrue
        """
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def send_weekly_menu_notification(
        self,
        menu_items: list[dict],
        start_date: date,
        end_date: date,
        notion_url: str,
    ) -> bool:
        """
        週間献立の通知を送信します。

        Args:
            menu_items: 献立アイテムのリスト
            start_date: 週の開始日
            end_date: 週の終了日
            notion_url: NotionデータベースのURL

        Returns:
            送信成功ならTrue
        """
        # 日付ごとにグループ化
        menu_by_date: dict[str, list[dict]] = {}
        shopping_items: set[str] = set()

        for item in menu_items:
            date_str = item.get("date", "")
            if date_str not in menu_by_date:
                menu_by_date[date_str] = []
            menu_by_date[date_str].append(item)

            # 買い物リストを集約
            shopping = item.get("shopping_list", "")
            if shopping:
                for ingredient in shopping.split(","):
                    ingredient = ingredient.strip()
                    if ingredient:
                        shopping_items.add(ingredient)

        # Block Kit メッセージを構築
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🍽️ 今週の献立 ({start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')})",
                    "emoji": True,
                },
            },
            {"type": "divider"},
        ]

        # 曜日の日本語マッピング
        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]

        # 日付順にソートして表示
        for date_str in sorted(menu_by_date.keys()):
            items = menu_by_date[date_str]
            try:
                d = date.fromisoformat(date_str)
                weekday = weekday_names[d.weekday()]
                date_display = f"{d.strftime('%m/%d')} ({weekday})"
            except ValueError:
                date_display = date_str

            # その日の献立を整形
            dishes = []
            for item in items:
                category = item.get("category", "")
                dish_name = item.get("dish_name", "")
                status = item.get("status", "提案")
                status_emoji = self._get_status_emoji(status)
                dishes.append(f"• {category}: {dish_name} {status_emoji}")

            dishes_text = "\n".join(dishes)

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{date_display}*\n{dishes_text}",
                    },
                }
            )

        # 買い物リスト
        if shopping_items:
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🛒 買い物リスト*\n{', '.join(sorted(shopping_items))}",
                    },
                }
            )

        # Notionへのリンク
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{notion_url}|📝 Notionで確認・編集する>",
                },
            }
        )

        fallback_text = f"今週の献立 ({start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}) が準備できました"

        return self.send_message(fallback_text, blocks)

    def send_daily_reminder(
        self,
        today_date: date,
        today_menu: list[dict],
        notion_url: str,
    ) -> bool:
        """
        日次の実績確認リマインダーを送信します。

        Args:
            today_date: 今日の日付
            today_menu: 今日の献立リスト
            notion_url: 実績入力用のNotionURL

        Returns:
            送信成功ならTrue
        """
        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekday_names[today_date.weekday()]
        date_display = f"{today_date.strftime('%m/%d')} ({weekday})"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🍴 今日のご飯はどうでしたか？",
                    "emoji": True,
                },
            },
            {"type": "divider"},
        ]

        if today_menu:
            dishes = []
            for item in today_menu:
                category = item.get("category", "")
                dish_name = item.get("dish_name", "")
                dishes.append(f"• {category}: {dish_name}")

            dishes_text = "\n".join(dishes)
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📋 {date_display} の予定メニュー*\n{dishes_text}",
                    },
                }
            )
        else:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{date_display}* の献立予定はありません。",
                    },
                }
            )

        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"実際に食べたものを記録してください！\n<{notion_url}|📝 Notionで実績を入力する>",
                },
            }
        )

        fallback_text = f"今日 ({date_display}) のご飯の実績を記録してください"

        return self.send_message(fallback_text, blocks)

    def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """
        エラー通知を送信します。

        Args:
            error_message: エラーメッセージ
            context: エラーの発生コンテキスト

        Returns:
            送信成功ならTrue
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Dinner-Aide エラー通知",
                    "emoji": True,
                },
            },
            {"type": "divider"},
        ]

        if context:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*発生箇所:* {context}",
                    },
                }
            )

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*エラー内容:*\n```{error_message}```",
                },
            }
        )

        fallback_text = f"Dinner-Aide でエラーが発生しました: {error_message}"

        return self.send_message(fallback_text, blocks)

    def send_skip_notification(self, reason: str, week_range: str) -> bool:
        """
        献立生成スキップの通知を送信します。

        Args:
            reason: スキップした理由
            week_range: 対象の週の範囲

        Returns:
            送信成功ならTrue
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📌 献立生成スキップのお知らせ",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*対象週:* {week_range}\n*理由:* {reason}",
                },
            },
        ]

        fallback_text = f"献立生成をスキップしました: {reason}"

        return self.send_message(fallback_text, blocks)

    def _get_status_emoji(self, status: str) -> str:
        """ステータスに応じた絵文字を返す"""
        status_emojis = {
            "提案": "💡",
            "確定": "✅",
            "外食・予定あり": "🍽️",
        }
        return status_emojis.get(status, "")

    def test_connection(self) -> bool:
        """
        Slack Webhookへの接続をテストします。

        Returns:
            接続成功ならTrue
        """
        return self.send_message("🔧 Dinner-Aide 接続テスト: 正常に動作しています")
