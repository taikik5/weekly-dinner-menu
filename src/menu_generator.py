"""
週間献立生成ロジック

既存の予定を尊重しつつ、空いた枠をAIで埋める「差分生成」を行います。
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from config.settings import HISTORY_WEEKS
from src.notion_client import NotionClientWrapper, ProposedDish
from src.openai_client import GeneratedMenuItem, OpenAIClientWrapper
from src.slack_client import SlackClientWrapper

logger = logging.getLogger(__name__)


@dataclass
class MenuGenerationResult:
    """献立生成の結果"""

    generated_count: int  # 生成した献立数
    skipped: bool  # 生成をスキップしたか
    skip_reason: str  # スキップ理由
    errors: list[str]  # エラーメッセージリスト


class WeeklyMenuGenerator:
    """
    週間献立生成器。

    1. 次週の既存予定を確認
    2. 空いている日付を特定
    3. 過去の実績を取得
    4. AIで献立を生成
    5. Notionに保存
    6. Slackに通知
    """

    def __init__(
        self,
        notion_client: NotionClientWrapper | None = None,
        openai_client: OpenAIClientWrapper | None = None,
        slack_client: SlackClientWrapper | None = None,
    ):
        """
        生成器を初期化します。

        Args:
            notion_client: Notionクライアント
            openai_client: OpenAIクライアント
            slack_client: Slackクライアント
        """
        self.notion = notion_client or NotionClientWrapper()
        self.openai = openai_client or OpenAIClientWrapper()
        self.slack = slack_client or SlackClientWrapper()

    def generate_for_next_week(
        self, reference_date: date | None = None, from_today: bool = False
    ) -> MenuGenerationResult:
        """
        献立を生成します。

        Args:
            reference_date: 基準日（省略時は今日）
            from_today: Trueの場合、基準日から7日間の献立を生成。
                       Falseの場合、次週（月曜〜日曜）の献立を生成。

        Returns:
            生成結果
        """
        today = reference_date or date.today()

        if from_today:
            # 手動実行モード: 今日から7日間
            start_date = today
            end_date = today + timedelta(days=6)
        else:
            # 自動実行モード: 次週の月曜〜日曜
            start_date, end_date = self._get_next_week_range(today)

        logger.info(
            f"Generating menu for {start_date.isoformat()} to {end_date.isoformat()}"
        )

        errors: list[str] = []

        # Step 0: 自動実行モードの場合、既存の「提案」ステータスのデータを削除（上書き）
        if not from_today:
            try:
                deleted, failed = self.notion.delete_proposed_dishes_by_date_range(
                    start_date, end_date, status_filter="提案"
                )
                if deleted > 0:
                    logger.info(
                        f"Deleted {deleted} existing proposals for overwrite "
                        f"(failed: {failed})"
                    )
                if failed > 0:
                    errors.append(f"既存提案の削除に一部失敗: {failed}件")
            except Exception as e:
                logger.error(f"Failed to delete existing proposals: {e}")
                errors.append(f"既存提案の削除に失敗: {e}")

        # Step 1: 既存の予定を取得
        try:
            existing_dishes = self.notion.get_proposed_dishes_by_date_range(
                start_date, end_date
            )
        except Exception as e:
            logger.error(f"Failed to fetch existing dishes: {e}")
            return MenuGenerationResult(
                generated_count=0,
                skipped=True,
                skip_reason=f"既存予定の取得に失敗: {e}",
                errors=[str(e)],
            )

        # Step 2: 空いている日付を特定
        dates_with_plans = self._get_dates_with_plans(existing_dishes)
        all_dates = self._get_date_range(start_date, end_date)
        dates_to_fill = [d for d in all_dates if d not in dates_with_plans]

        logger.info(
            f"Dates with existing plans: {len(dates_with_plans)}, "
            f"Dates to fill: {len(dates_to_fill)}"
        )

        # すべての日に予定がある場合はスキップ
        if not dates_to_fill:
            week_range = f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
            skip_reason = "すべての日に予定が入っています"

            try:
                self.slack.send_skip_notification(skip_reason, week_range)
            except Exception as e:
                logger.error(f"Failed to send skip notification: {e}")
                errors.append(f"スキップ通知の送信に失敗: {e}")

            # 既存の予定のみで通知
            self._send_weekly_notification(
                existing_dishes, start_date, end_date, errors
            )

            return MenuGenerationResult(
                generated_count=0,
                skipped=True,
                skip_reason=skip_reason,
                errors=errors,
            )

        # Step 3: 過去の実績を取得
        history_start = today - timedelta(weeks=HISTORY_WEEKS)
        try:
            recent_history = self.notion.get_structured_history_by_date_range(
                history_start, today
            )
        except Exception as e:
            logger.warning(f"Failed to fetch history, continuing without it: {e}")
            recent_history = []

        # Step 4: AIで献立を生成
        existing_plans = [
            {
                "date": dish.date.isoformat(),
                "dish_name": dish.dish_name,
                "category": dish.category,
                "status": dish.status,
            }
            for dish in existing_dishes
        ]

        history_data = [
            {
                "date": h.date.isoformat(),
                "dish_name": h.dish_name,
                "category": h.category,
            }
            for h in recent_history
        ]

        try:
            generated_items = self.openai.generate_weekly_menu(
                dates_to_fill=dates_to_fill,
                existing_plans=existing_plans,
                recent_history=history_data,
            )
        except Exception as e:
            logger.error(f"Failed to generate menu: {e}")
            return MenuGenerationResult(
                generated_count=0,
                skipped=True,
                skip_reason=f"献立生成に失敗: {e}",
                errors=[str(e)],
            )

        if not generated_items:
            logger.warning("No menu items were generated")
            return MenuGenerationResult(
                generated_count=0,
                skipped=True,
                skip_reason="AIから献立が生成されませんでした",
                errors=["AIから献立が生成されませんでした"],
            )

        # Step 5: Notionに保存
        saved_count = 0
        saved_dishes: list[ProposedDish] = []

        for item in generated_items:
            try:
                dish = ProposedDish(
                    id=None,
                    dish_name=item.dish_name,
                    date=item.date,
                    category=item.category,
                    status="提案",
                    shopping_list=item.shopping_list,
                )
                page_id = self.notion.create_proposed_dish(dish)
                dish.id = page_id
                saved_dishes.append(dish)
                saved_count += 1
                logger.info(f"Saved dish: {item.dish_name} for {item.date}")
            except Exception as e:
                logger.error(f"Failed to save dish {item.dish_name}: {e}")
                errors.append(f"保存に失敗: {item.dish_name} - {e}")

        # Step 6: Slackに通知（既存 + 新規生成分）
        all_dishes = existing_dishes + saved_dishes
        self._send_weekly_notification(all_dishes, start_date, end_date, errors)

        return MenuGenerationResult(
            generated_count=saved_count,
            skipped=False,
            skip_reason="",
            errors=errors,
        )

    def _get_next_week_range(self, reference_date: date) -> tuple[date, date]:
        """
        次週の月曜日から日曜日の範囲を取得します。

        Args:
            reference_date: 基準日

        Returns:
            (開始日, 終了日)のタプル
        """
        # 次の月曜日を見つける
        days_until_monday = (7 - reference_date.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # 今日が月曜なら来週の月曜

        next_monday = reference_date + timedelta(days=days_until_monday)
        next_sunday = next_monday + timedelta(days=6)

        return next_monday, next_sunday

    def _get_date_range(self, start_date: date, end_date: date) -> list[date]:
        """
        開始日から終了日までの日付リストを生成します。
        """
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates

    def _get_dates_with_plans(self, dishes: list[ProposedDish]) -> set[date]:
        """
        予定がある日付のセットを取得します。
        「確定」または「外食・予定あり」のステータスを持つ日付を返します。
        """
        dates_with_confirmed = set()
        for dish in dishes:
            if dish.status in ["確定", "外食・予定あり"]:
                dates_with_confirmed.add(dish.date)
        return dates_with_confirmed

    def _send_weekly_notification(
        self,
        dishes: list[ProposedDish],
        start_date: date,
        end_date: date,
        errors: list[str],
    ) -> None:
        """
        週間献立の通知を送信します。
        """
        if not dishes:
            return

        menu_items = [
            {
                "date": dish.date.isoformat(),
                "dish_name": dish.dish_name,
                "category": dish.category,
                "status": dish.status,
                "shopping_list": dish.shopping_list,
            }
            for dish in dishes
        ]

        try:
            notion_url = self.notion.get_proposed_database_url()
            self.slack.send_weekly_menu_notification(
                menu_items=menu_items,
                start_date=start_date,
                end_date=end_date,
                notion_url=notion_url,
            )
            logger.info("Sent weekly menu notification to Slack")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            errors.append(f"Slack通知の送信に失敗: {e}")
