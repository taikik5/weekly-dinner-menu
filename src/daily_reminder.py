"""
日次実績確認リマインダー

毎日19:00に実行され、以下の処理を行います:
1. 未処理の実績入力を構造化して保存
2. 今日の献立と実績入力のリマインドをSlackに送信
"""

import logging
from dataclasses import dataclass
from datetime import date

from src.notion_client import NotionClientWrapper
from src.openai_client import OpenAIClientWrapper
from src.preprocessor import ActualDataPreprocessor
from src.slack_client import SlackClientWrapper

logger = logging.getLogger(__name__)


@dataclass
class DailyReminderResult:
    """日次リマインダーの結果"""

    sent: bool  # 送信成功したか
    menu_count: int  # 今日の献立数
    error: str  # エラーメッセージ
    preprocessed_count: int = 0  # 処理した実績入力数
    structured_count: int = 0  # 作成した構造化履歴数


class DailyReminderSender:
    """
    日次実績確認リマインダーを送信します。

    1. 未処理の実績入力を構造化して保存
    2. 今日の献立予定を取得
    3. Slackへリマインダーを送信
    """

    def __init__(
        self,
        notion_client: NotionClientWrapper | None = None,
        openai_client: OpenAIClientWrapper | None = None,
        slack_client: SlackClientWrapper | None = None,
    ):
        """
        リマインダー送信器を初期化します。

        Args:
            notion_client: Notionクライアント
            openai_client: OpenAIクライアント（実績構造化用）
            slack_client: Slackクライアント
        """
        self.notion = notion_client or NotionClientWrapper()
        self.openai = openai_client or OpenAIClientWrapper()
        self.slack = slack_client or SlackClientWrapper()

    def send_reminder(self, target_date: date | None = None) -> DailyReminderResult:
        """
        日次リマインダーを送信します。

        Args:
            target_date: 対象日（省略時は今日）

        Returns:
            送信結果
        """
        today = target_date or date.today()

        logger.info(f"Sending daily reminder for {today.isoformat()}")

        # Step 1: 未処理の実績入力を構造化
        preprocessed_count = 0
        structured_count = 0
        try:
            preprocessor = ActualDataPreprocessor(
                notion_client=self.notion,
                openai_client=self.openai,
            )
            preprocess_result = preprocessor.process_all_unprocessed()
            preprocessed_count = preprocess_result.processed_count
            structured_count = preprocess_result.created_count

            logger.info(
                f"Preprocessing complete: "
                f"processed={preprocessed_count}, created={structured_count}"
            )

            if preprocess_result.errors:
                for error in preprocess_result.errors:
                    logger.warning(f"Preprocessing warning: {error}")

        except Exception as e:
            logger.error(f"Failed to preprocess raw inputs: {e}")
            # 前処理が失敗してもリマインダー送信は続行

        # Step 2: 今日の献立を取得
        try:
            today_dishes = self.notion.get_proposed_dishes_by_date(today)
        except Exception as e:
            logger.error(f"Failed to fetch today's dishes: {e}")
            return DailyReminderResult(
                sent=False,
                menu_count=0,
                error=f"今日の献立取得に失敗: {e}",
                preprocessed_count=preprocessed_count,
                structured_count=structured_count,
            )

        # 献立をSlack用の形式に変換
        menu_items = [
            {
                "dish_name": dish.dish_name,
                "category": dish.category,
                "status": dish.status,
            }
            for dish in today_dishes
        ]

        # 実績入力用のNotion URLを取得
        try:
            notion_url = self.notion.get_raw_input_database_url()
        except Exception as e:
            logger.warning(f"Failed to get Notion URL: {e}")
            notion_url = ""

        # Step 3: Slackにリマインダーを送信
        try:
            success = self.slack.send_daily_reminder(
                today_date=today,
                today_menu=menu_items,
                notion_url=notion_url,
            )

            if success:
                logger.info(
                    f"Daily reminder sent successfully. Menu items: {len(menu_items)}"
                )
                return DailyReminderResult(
                    sent=True,
                    menu_count=len(menu_items),
                    error="",
                    preprocessed_count=preprocessed_count,
                    structured_count=structured_count,
                )
            else:
                logger.error("Failed to send daily reminder to Slack")
                return DailyReminderResult(
                    sent=False,
                    menu_count=len(menu_items),
                    error="Slackへの送信に失敗しました",
                    preprocessed_count=preprocessed_count,
                    structured_count=structured_count,
                )

        except Exception as e:
            logger.error(f"Failed to send daily reminder: {e}")
            return DailyReminderResult(
                sent=False,
                menu_count=len(menu_items),
                error=f"リマインダー送信に失敗: {e}",
                preprocessed_count=preprocessed_count,
                structured_count=structured_count,
            )
