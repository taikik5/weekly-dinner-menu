"""
Notion API クライアント

3つのデータベースとの通信を担当するクラスを提供します。
- Proposed_Dishes: 提案メニューテーブル
- Raw_Actual_Input: 実績入力テーブル
- Structured_Actual_History: 実績履歴テーブル
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from notion_client import Client

from config.settings import (
    DB_ID_PROPOSED,
    DB_ID_RAW,
    DB_ID_STRUCTURED,
    NOTION_TOKEN,
)


@dataclass
class ProposedDish:
    """提案メニューテーブルのレコード"""

    id: str | None  # Notion page ID (新規作成時はNone)
    dish_name: str  # 料理名
    date: date  # 実施予定日
    category: str  # 区分: 主菜/副菜/汁物/その他
    status: str  # ステータス: 提案/確定/外食・予定あり
    shopping_list: str = ""  # 買い物リスト


@dataclass
class RawActualInput:
    """実績入力テーブルのレコード"""

    id: str | None  # Notion page ID
    date: date  # 食べた日
    food_eaten: str  # 食べたもの（自由記述）
    is_processed: bool = False  # 処理済みフラグ


@dataclass
class StructuredActualHistory:
    """実績履歴テーブルのレコード"""

    id: str | None  # Notion page ID
    dish_name: str  # 構造化された料理名
    date: date  # 食べた日
    category: str  # 区分: 主菜/副菜/その他


class NotionClientWrapper:
    """
    Notion APIとの通信を行うラッパークラス。
    3つのデータベースへのCRUD操作を提供します。
    """

    def __init__(self, token: str | None = None):
        """
        クライアントを初期化します。

        Args:
            token: Notion API トークン。省略時は環境変数から取得。
        """
        self.token = token or NOTION_TOKEN
        if not self.token:
            raise ValueError("Notion token is required")

        self.client = Client(auth=self.token)

        # Database IDs
        self.db_proposed = DB_ID_PROPOSED
        self.db_raw = DB_ID_RAW
        self.db_structured = DB_ID_STRUCTURED

    # =========================================================================
    # Proposed Dishes (提案メニューテーブル) Operations
    # =========================================================================

    def get_proposed_dishes_by_date_range(
        self, start_date: date, end_date: date
    ) -> list[ProposedDish]:
        """
        指定した日付範囲の提案メニューを取得します。

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            提案メニューのリスト
        """
        try:
            # Notion SDK v2.x では query_paginated を使用
            pages = list(self.client.databases.query_paginated(
                database_id=self.db_proposed,
                filter={
                    "and": [
                        {
                            "property": "日付",
                            "date": {"on_or_after": start_date.isoformat()},
                        },
                        {
                            "property": "日付",
                            "date": {"on_or_before": end_date.isoformat()},
                        },
                    ]
                },
                sorts=[{"property": "日付", "direction": "ascending"}],
            ))
        except AttributeError:
            # フォールバック: query メソッドが存在する場合
            response = self.client.databases.query(
                database_id=self.db_proposed,
                filter={
                    "and": [
                        {
                            "property": "日付",
                            "date": {"on_or_after": start_date.isoformat()},
                        },
                        {
                            "property": "日付",
                            "date": {"on_or_before": end_date.isoformat()},
                        },
                    ]
                },
                sorts=[{"property": "日付", "direction": "ascending"}],
            )
            pages = response["results"]

        return [self._parse_proposed_dish(page) for page in pages]

    def get_proposed_dishes_by_date(self, target_date: date) -> list[ProposedDish]:
        """
        指定した日付の提案メニューを取得します。

        Args:
            target_date: 対象日

        Returns:
            提案メニューのリスト
        """
        try:
            # Notion SDK v2.x では query_paginated を使用
            pages = list(self.client.databases.query_paginated(
                database_id=self.db_proposed,
                filter={"property": "日付", "date": {"equals": target_date.isoformat()}},
            ))
        except AttributeError:
            # フォールバック: query メソッドが存在する場合
            response = self.client.databases.query(
                database_id=self.db_proposed,
                filter={"property": "日付", "date": {"equals": target_date.isoformat()}},
            )
            pages = response["results"]

        return [self._parse_proposed_dish(page) for page in pages]

    def create_proposed_dish(self, dish: ProposedDish) -> str:
        """
        新しい提案メニューを作成します。

        Args:
            dish: 作成する料理データ

        Returns:
            作成されたページのID
        """
        properties: dict[str, Any] = {
            "料理名": {"title": [{"text": {"content": dish.dish_name}}]},
            "日付": {"date": {"start": dish.date.isoformat()}},
            "区分": {"multi_select": [{"name": dish.category}]},
            "ステータス": {"multi_select": [{"name": dish.status}]},
        }

        if dish.shopping_list:
            properties["買い物リスト"] = {
                "rich_text": [{"text": {"content": dish.shopping_list}}]
            }

        response = self.client.pages.create(
            parent={"database_id": self.db_proposed},
            properties=properties,
        )

        return response["id"]

    def update_proposed_dish_status(self, page_id: str, new_status: str) -> None:
        """
        提案メニューのステータスを更新します。

        Args:
            page_id: 更新するページのID
            new_status: 新しいステータス
        """
        self.client.pages.update(
            page_id=page_id,
            properties={"ステータス": {"multi_select": [{"name": new_status}]}},
        )

    def delete_proposed_dishes_by_date_range(
        self, start_date: date, end_date: date, status_filter: str = "提案"
    ) -> tuple[int, int]:
        """
        指定した日付範囲・ステータスの提案メニューを削除します。

        Args:
            start_date: 開始日
            end_date: 終了日
            status_filter: 削除対象のステータス（デフォルト: 「提案」）

        Returns:
            (削除成功数, 削除失敗数)
        """
        # 該当範囲のデータを取得
        dishes = self.get_proposed_dishes_by_date_range(start_date, end_date)

        # 指定ステータスのみをフィルタ
        target_dishes = [d for d in dishes if d.status == status_filter]

        success = 0
        failed = 0

        for dish in target_dishes:
            if dish.id and self._archive_page(dish.id):
                success += 1
            else:
                failed += 1

        return success, failed

    def _parse_proposed_dish(self, page: dict[str, Any]) -> ProposedDish:
        """Notionページデータを ProposedDish に変換"""
        props = page["properties"]

        # 料理名 (Title)
        dish_name = ""
        if props["料理名"]["title"]:
            dish_name = props["料理名"]["title"][0]["plain_text"]

        # 日付
        date_str = props["日付"]["date"]["start"] if props["日付"]["date"] else None
        dish_date = (
            datetime.fromisoformat(date_str).date() if date_str else date.today()
        )

        # 区分 (multi_select または select に対応)
        if props["区分"].get("multi_select"):
            category = props["区分"]["multi_select"][0]["name"] if props["区分"]["multi_select"] else "その他"
        else:
            category = props["区分"]["select"]["name"] if props["区分"]["select"] else "その他"

        # ステータス (multi_select または select に対応)
        if props["ステータス"].get("multi_select"):
            status = (
                props["ステータス"]["multi_select"][0]["name"]
                if props["ステータス"]["multi_select"]
                else "提案"
            )
        else:
            status = (
                props["ステータス"]["select"]["name"]
                if props["ステータス"]["select"]
                else "提案"
            )

        # 買い物リスト
        shopping_list = ""
        if props["買い物リスト"]["rich_text"]:
            shopping_list = props["買い物リスト"]["rich_text"][0]["plain_text"]

        return ProposedDish(
            id=page["id"],
            dish_name=dish_name,
            date=dish_date,
            category=category,
            status=status,
            shopping_list=shopping_list,
        )

    # =========================================================================
    # Raw Actual Input (実績入力テーブル) Operations
    # =========================================================================

    def get_unprocessed_raw_inputs(self) -> list[RawActualInput]:
        """
        処理済みでない実績入力を全取得します。

        Returns:
            未処理の実績入力リスト
        """
        try:
            # Notion SDK v2.x では query_paginated を使用
            pages = list(self.client.databases.query_paginated(
                database_id=self.db_raw,
                filter={"property": "処理済み", "checkbox": {"equals": False}},
                sorts=[{"property": "日付", "direction": "ascending"}],
            ))
        except AttributeError:
            # フォールバック: query メソッドが存在する場合
            response = self.client.databases.query(
                database_id=self.db_raw,
                filter={"property": "処理済み", "checkbox": {"equals": False}},
                sorts=[{"property": "日付", "direction": "ascending"}],
            )
            pages = response["results"]

        return [self._parse_raw_input(page) for page in pages]

    def mark_raw_input_as_processed(self, page_id: str) -> None:
        """
        実績入力を処理済みにマークします。

        Args:
            page_id: 更新するページのID
        """
        self.client.pages.update(
            page_id=page_id,
            properties={"処理済み": {"checkbox": True}},
        )

    def _parse_raw_input(self, page: dict[str, Any]) -> RawActualInput:
        """Notionページデータを RawActualInput に変換"""
        props = page["properties"]

        # 食べたもの (Title)
        food_eaten = ""
        if props["食べたもの"]["title"]:
            food_eaten = props["食べたもの"]["title"][0]["plain_text"]

        # 日付
        date_str = props["日付"]["date"]["start"] if props["日付"]["date"] else None
        input_date = (
            datetime.fromisoformat(date_str).date() if date_str else date.today()
        )

        # 処理済み
        is_processed = props["処理済み"]["checkbox"]

        return RawActualInput(
            id=page["id"],
            date=input_date,
            food_eaten=food_eaten,
            is_processed=is_processed,
        )

    # =========================================================================
    # Structured Actual History (実績履歴テーブル) Operations
    # =========================================================================

    def get_structured_history_by_date_range(
        self, start_date: date, end_date: date
    ) -> list[StructuredActualHistory]:
        """
        指定した日付範囲の実績履歴を取得します。

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            実績履歴のリスト
        """
        try:
            # Notion SDK v2.x では query_paginated を使用
            pages = list(self.client.databases.query_paginated(
                database_id=self.db_structured,
                filter={
                    "and": [
                        {
                            "property": "日付",
                            "date": {"on_or_after": start_date.isoformat()},
                        },
                        {
                            "property": "日付",
                            "date": {"on_or_before": end_date.isoformat()},
                        },
                    ]
                },
                sorts=[{"property": "日付", "direction": "descending"}],
            ))
        except AttributeError:
            # フォールバック: query メソッドが存在する場合
            response = self.client.databases.query(
                database_id=self.db_structured,
                filter={
                    "and": [
                        {
                            "property": "日付",
                            "date": {"on_or_after": start_date.isoformat()},
                        },
                        {
                            "property": "日付",
                            "date": {"on_or_before": end_date.isoformat()},
                        },
                    ]
                },
                sorts=[{"property": "日付", "direction": "descending"}],
            )
            pages = response["results"]

        return [self._parse_structured_history(page) for page in pages]

    def create_structured_history(self, history: StructuredActualHistory) -> str:
        """
        新しい実績履歴を作成します。

        Args:
            history: 作成する履歴データ

        Returns:
            作成されたページのID
        """
        properties = {
            "料理名": {"title": [{"text": {"content": history.dish_name}}]},
            "日付": {"date": {"start": history.date.isoformat()}},
            "区分": {"multi_select": [{"name": history.category}]},
        }

        response = self.client.pages.create(
            parent={"database_id": self.db_structured},
            properties=properties,
        )

        return response["id"]

    def _parse_structured_history(
        self, page: dict[str, Any]
    ) -> StructuredActualHistory:
        """Notionページデータを StructuredActualHistory に変換"""
        props = page["properties"]

        # 料理名 (Title)
        dish_name = ""
        if props["料理名"]["title"]:
            dish_name = props["料理名"]["title"][0]["plain_text"]

        # 日付
        date_str = props["日付"]["date"]["start"] if props["日付"]["date"] else None
        history_date = (
            datetime.fromisoformat(date_str).date() if date_str else date.today()
        )

        # 区分 (multi_select または select に対応)
        if props["区分"].get("multi_select"):
            category = props["区分"]["multi_select"][0]["name"] if props["区分"]["multi_select"] else "その他"
        else:
            category = props["区分"]["select"]["name"] if props["区分"]["select"] else "その他"

        return StructuredActualHistory(
            id=page["id"],
            dish_name=dish_name,
            date=history_date,
            category=category,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_database_url(self, database_id: str) -> str:
        """
        データベースのNotionURLを生成します。

        Args:
            database_id: データベースID

        Returns:
            NotionのURL
        """
        # ハイフンを除去してURLを生成
        clean_id = database_id.replace("-", "")
        return f"https://www.notion.so/{clean_id}"

    def get_proposed_database_url(self) -> str:
        """提案メニューテーブルのURLを取得"""
        return self.get_database_url(self.db_proposed)

    def get_raw_input_database_url(self) -> str:
        """実績入力テーブルのURLを取得"""
        return self.get_database_url(self.db_raw)

    def test_connection(self) -> bool:
        """
        Notion APIへの接続をテストします。

        Returns:
            接続成功ならTrue
        """
        try:
            # 各データベースへのアクセスをテスト
            self.client.databases.retrieve(database_id=self.db_proposed)
            self.client.databases.retrieve(database_id=self.db_raw)
            self.client.databases.retrieve(database_id=self.db_structured)
            return True
        except Exception:
            return False

    # =========================================================================
    # Data Reset Methods (検証環境専用)
    # =========================================================================

    def _get_all_pages_in_database(self, database_id: str) -> list[str]:
        """
        データベース内の全ページIDを取得します。

        Args:
            database_id: データベースID

        Returns:
            ページIDのリスト
        """
        try:
            pages = list(self.client.databases.query_paginated(
                database_id=database_id,
            ))
        except AttributeError:
            response = self.client.databases.query(
                database_id=database_id,
            )
            pages = response["results"]

        return [page["id"] for page in pages]

    def _archive_page(self, page_id: str) -> bool:
        """
        ページをアーカイブ（削除）します。

        Args:
            page_id: ページID

        Returns:
            成功ならTrue
        """
        try:
            self.client.pages.update(page_id=page_id, archived=True)
            return True
        except Exception:
            return False

    def reset_proposed_dishes(self) -> tuple[int, int]:
        """
        提案メニューテーブルの全データを削除します。

        Returns:
            (削除成功数, 削除失敗数)
        """
        page_ids = self._get_all_pages_in_database(self.db_proposed)
        success = 0
        failed = 0

        for page_id in page_ids:
            if self._archive_page(page_id):
                success += 1
            else:
                failed += 1

        return success, failed

    def reset_raw_inputs(self) -> tuple[int, int]:
        """
        実績入力テーブルの全データを削除します。

        Returns:
            (削除成功数, 削除失敗数)
        """
        page_ids = self._get_all_pages_in_database(self.db_raw)
        success = 0
        failed = 0

        for page_id in page_ids:
            if self._archive_page(page_id):
                success += 1
            else:
                failed += 1

        return success, failed

    def reset_structured_history(self) -> tuple[int, int]:
        """
        実績履歴テーブルの全データを削除します。

        Returns:
            (削除成功数, 削除失敗数)
        """
        page_ids = self._get_all_pages_in_database(self.db_structured)
        success = 0
        failed = 0

        for page_id in page_ids:
            if self._archive_page(page_id):
                success += 1
            else:
                failed += 1

        return success, failed

    def reset_all_databases(self) -> dict[str, tuple[int, int]]:
        """
        全データベースのデータを削除します。

        Returns:
            各テーブルの (削除成功数, 削除失敗数) の辞書
        """
        return {
            "proposed_dishes": self.reset_proposed_dishes(),
            "raw_inputs": self.reset_raw_inputs(),
            "structured_history": self.reset_structured_history(),
        }

    # =========================================================================
    # Test Data Creation Methods (検証環境専用)
    # =========================================================================

    def create_test_raw_input(self, food_eaten: str, eaten_date: date) -> str:
        """
        テスト用の実績入力データを作成します。

        Args:
            food_eaten: 食べたもの（自由記述）
            eaten_date: 食べた日

        Returns:
            作成されたページのID
        """
        properties = {
            "食べたもの": {"title": [{"text": {"content": food_eaten}}]},
            "日付": {"date": {"start": eaten_date.isoformat()}},
            "処理済み": {"checkbox": False},
        }

        response = self.client.pages.create(
            parent={"database_id": self.db_raw},
            properties=properties,
        )

        return response["id"]
