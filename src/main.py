"""
Dinner-Aide メインエントリーポイント

GitHub Actionsまたはコマンドラインから実行されます。
"""

import argparse
import logging
import sys
from datetime import date

from config.settings import is_development, is_production, ENV, validate_config
from src.daily_reminder import DailyReminderSender
from src.menu_generator import WeeklyMenuGenerator
from src.notion_client import NotionClientWrapper
from src.openai_client import OpenAIClientWrapper
from src.preprocessor import ActualDataPreprocessor
from src.slack_client import SlackClientWrapper

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_weekly_generation(
    reference_date: date | None = None, from_today: bool = False
) -> int:
    """
    週間献立生成フローを実行します。

    1. 実績データの構造化
    2. 献立の生成とSlack通知

    Args:
        reference_date: 基準日（テスト用）
        from_today: Trueの場合、基準日から7日間の献立を生成

    Returns:
        終了コード（0: 成功, 1: 失敗）
    """
    logger.info("=" * 50)
    logger.info("Starting weekly menu generation flow")
    logger.info("=" * 50)

    # 設定の検証
    errors = validate_config()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return 1

    # クライアントの初期化
    try:
        notion = NotionClientWrapper()
        openai = OpenAIClientWrapper()
        slack = SlackClientWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        return 1

    # Step 1: 実績データの構造化
    logger.info("-" * 30)
    logger.info("Step 1: Processing raw actual data")
    logger.info("-" * 30)

    preprocessor = ActualDataPreprocessor(
        notion_client=notion, openai_client=openai
    )
    preprocess_result = preprocessor.process_all_unprocessed()

    logger.info(
        f"Preprocessing complete: "
        f"processed={preprocess_result.processed_count}, "
        f"created={preprocess_result.created_count}"
    )

    if preprocess_result.errors:
        for error in preprocess_result.errors:
            logger.warning(f"Preprocessing warning: {error}")

    # Step 2 & 3: 献立生成と通知
    logger.info("-" * 30)
    logger.info("Step 2-3: Generating menu and notifying")
    logger.info("-" * 30)

    generator = WeeklyMenuGenerator(
        notion_client=notion,
        openai_client=openai,
        slack_client=slack,
    )

    generation_result = generator.generate_for_next_week(reference_date, from_today=from_today)

    if generation_result.skipped:
        logger.info(f"Menu generation skipped: {generation_result.skip_reason}")
    else:
        logger.info(f"Generated {generation_result.generated_count} menu items")

    if generation_result.errors:
        for error in generation_result.errors:
            logger.error(f"Generation error: {error}")

    logger.info("=" * 50)
    logger.info("Weekly menu generation flow completed")
    logger.info("=" * 50)

    # エラーがあっても部分的に成功していれば0を返す
    return 0


def run_daily_reminder(target_date: date | None = None) -> int:
    """
    日次リマインダーを実行します。

    1. 未処理の実績入力をStructured_Actual_Historyに構造化
    2. 今日の献立と実績入力のリマインドをSlackに送信

    Args:
        target_date: 対象日（テスト用）

    Returns:
        終了コード（0: 成功, 1: 失敗）
    """
    logger.info("=" * 50)
    logger.info("Starting daily reminder")
    logger.info("=" * 50)

    # 設定の検証
    errors = validate_config()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return 1

    # クライアントの初期化
    try:
        notion = NotionClientWrapper()
        openai = OpenAIClientWrapper()
        slack = SlackClientWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        return 1

    # リマインダー送信（内部で実績の構造化も実行）
    sender = DailyReminderSender(
        notion_client=notion,
        openai_client=openai,
        slack_client=slack,
    )

    result = sender.send_reminder(target_date)

    # 構造化処理の結果をログ出力
    if result.preprocessed_count > 0 or result.structured_count > 0:
        logger.info(
            f"Preprocessing: {result.preprocessed_count} raw inputs processed, "
            f"{result.structured_count} structured records created"
        )

    if result.sent:
        logger.info(f"Daily reminder sent successfully. Menu items: {result.menu_count}")
        return 0
    else:
        logger.error(f"Failed to send daily reminder: {result.error}")
        return 1


def test_connections() -> int:
    """
    全てのサービスへの接続をテストします。

    Returns:
        終了コード（0: 成功, 1: 失敗）
    """
    logger.info("Testing connections to all services...")

    # 設定の検証
    errors = validate_config()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return 1

    all_passed = True

    # Notion
    try:
        notion = NotionClientWrapper()
        if notion.test_connection():
            logger.info("✓ Notion connection: OK")
        else:
            logger.error("✗ Notion connection: FAILED")
            all_passed = False
    except Exception as e:
        logger.error(f"✗ Notion connection: FAILED - {e}")
        all_passed = False

    # OpenAI
    try:
        openai = OpenAIClientWrapper()
        if openai.test_connection():
            logger.info("✓ OpenAI connection: OK")
        else:
            logger.error("✗ OpenAI connection: FAILED")
            all_passed = False
    except Exception as e:
        logger.error(f"✗ OpenAI connection: FAILED - {e}")
        all_passed = False

    # Slack
    try:
        slack = SlackClientWrapper()
        if slack.test_connection():
            logger.info("✓ Slack connection: OK")
        else:
            logger.error("✗ Slack connection: FAILED")
            all_passed = False
    except Exception as e:
        logger.error(f"✗ Slack connection: FAILED - {e}")
        all_passed = False

    return 0 if all_passed else 1


def reset_databases(tables: list[str] | None = None, force: bool = False) -> int:
    """
    データベースをリセット（全データ削除）します。

    検証環境（ENV=development）でのみ実行可能です。
    本番環境では実行をブロックします。

    Args:
        tables: リセットするテーブル名のリスト。Noneの場合は全テーブル。
                有効値: "proposed", "raw", "structured", "all"
        force: 確認なしで実行するかどうか

    Returns:
        終了コード（0: 成功, 1: 失敗）
    """
    # 本番環境チェック
    if is_production():
        logger.error("=" * 50)
        logger.error("BLOCKED: Cannot reset databases in production environment!")
        logger.error(f"Current ENV: {ENV}")
        logger.error("This operation is only allowed in development environment.")
        logger.error("Set ENV=development to enable this feature.")
        logger.error("=" * 50)
        return 1

    if not is_development():
        logger.warning(f"Unknown environment: {ENV}. Treating as development.")

    logger.info("=" * 50)
    logger.info("Database Reset (Development Environment Only)")
    logger.info(f"Current ENV: {ENV}")
    logger.info("=" * 50)

    # 確認メッセージ
    if not force:
        logger.warning("This will DELETE ALL DATA from the specified tables.")
        logger.warning("This action cannot be undone.")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() != "yes":
            logger.info("Operation cancelled.")
            return 0

    # クライアント初期化
    try:
        notion = NotionClientWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {e}")
        return 1

    # リセット対象を決定
    if tables is None or "all" in tables:
        tables = ["proposed", "raw", "structured"]

    results = {}

    for table in tables:
        if table == "proposed":
            logger.info("Resetting Proposed_Dishes table...")
            success, failed = notion.reset_proposed_dishes()
            results["Proposed_Dishes"] = (success, failed)
            logger.info(f"  Deleted: {success}, Failed: {failed}")

        elif table == "raw":
            logger.info("Resetting Raw_Actual_Input table...")
            success, failed = notion.reset_raw_inputs()
            results["Raw_Actual_Input"] = (success, failed)
            logger.info(f"  Deleted: {success}, Failed: {failed}")

        elif table == "structured":
            logger.info("Resetting Structured_Actual_History table...")
            success, failed = notion.reset_structured_history()
            results["Structured_Actual_History"] = (success, failed)
            logger.info(f"  Deleted: {success}, Failed: {failed}")

        else:
            logger.warning(f"Unknown table: {table}")

    # サマリー
    logger.info("-" * 30)
    logger.info("Reset Summary:")
    total_deleted = 0
    total_failed = 0
    for table_name, (success, failed) in results.items():
        logger.info(f"  {table_name}: {success} deleted, {failed} failed")
        total_deleted += success
        total_failed += failed

    logger.info(f"Total: {total_deleted} deleted, {total_failed} failed")
    logger.info("=" * 50)

    return 0 if total_failed == 0 else 1


def seed_test_data() -> int:
    """
    検証用のテストデータを投入します。

    検証環境（ENV=development）でのみ実行可能です。

    Returns:
        終了コード（0: 成功, 1: 失敗）
    """
    from datetime import timedelta

    # 本番環境チェック
    if is_production():
        logger.error("BLOCKED: Cannot seed test data in production environment!")
        return 1

    logger.info("=" * 50)
    logger.info("Seeding Test Data (Development Environment Only)")
    logger.info("=" * 50)

    try:
        notion = NotionClientWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {e}")
        return 1

    # テストデータの定義
    today = date.today()
    test_raw_inputs = [
        ("キムチ鍋、しめのラーメン", today - timedelta(days=3)),
        ("焼き魚、ほうれん草のおひたし、味噌汁", today - timedelta(days=2)),
        ("カレーライス、サラダ", today - timedelta(days=1)),
        ("鶏の唐揚げ、ポテトサラダ、わかめスープ", today),
    ]

    created_count = 0
    for food_eaten, eaten_date in test_raw_inputs:
        try:
            page_id = notion.create_test_raw_input(food_eaten, eaten_date)
            logger.info(f"  Created: {food_eaten[:20]}... ({eaten_date})")
            created_count += 1
        except Exception as e:
            logger.error(f"  Failed to create: {food_eaten[:20]}... - {e}")

    logger.info("-" * 30)
    logger.info(f"Created {created_count} test records in Raw_Actual_Input")
    logger.info("=" * 50)

    return 0


def main() -> int:
    """
    メインエントリーポイント。
    コマンドライン引数に応じて処理を分岐します。
    """
    parser = argparse.ArgumentParser(
        description="Dinner-Aide: 献立自動生成・管理システム"
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # weekly コマンド
    weekly_parser = subparsers.add_parser(
        "weekly", help="週間献立生成フローを実行"
    )
    weekly_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="基準日（YYYY-MM-DD形式、テスト用）",
    )
    weekly_parser.add_argument(
        "--from-today",
        action="store_true",
        help="今日から7日間の献立を生成（手動実行用）",
    )

    # daily コマンド
    daily_parser = subparsers.add_parser(
        "daily", help="日次リマインダーを送信"
    )
    daily_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象日（YYYY-MM-DD形式、テスト用）",
    )

    # test コマンド
    subparsers.add_parser("test", help="接続テストを実行")

    # reset コマンド（検証環境専用）
    reset_parser = subparsers.add_parser(
        "reset", help="データベースをリセット（検証環境専用）"
    )
    reset_parser.add_argument(
        "--tables",
        type=str,
        nargs="+",
        default=["all"],
        choices=["proposed", "raw", "structured", "all"],
        help="リセットするテーブル（デフォルト: all）",
    )
    reset_parser.add_argument(
        "--force",
        action="store_true",
        help="確認なしで実行",
    )

    # seed コマンド（検証環境専用）
    subparsers.add_parser(
        "seed", help="テストデータを投入（検証環境専用）"
    )

    args = parser.parse_args()

    if args.command == "weekly":
        ref_date = None
        if args.date:
            try:
                ref_date = date.fromisoformat(args.date)
            except ValueError:
                logger.error(f"Invalid date format: {args.date}")
                return 1
        from_today = getattr(args, "from_today", False)
        return run_weekly_generation(ref_date, from_today=from_today)

    elif args.command == "daily":
        target = None
        if args.date:
            try:
                target = date.fromisoformat(args.date)
            except ValueError:
                logger.error(f"Invalid date format: {args.date}")
                return 1
        return run_daily_reminder(target)

    elif args.command == "test":
        return test_connections()

    elif args.command == "reset":
        return reset_databases(tables=args.tables, force=args.force)

    elif args.command == "seed":
        return seed_test_data()

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
