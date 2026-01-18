"""
OpenAI API クライアント

献立生成と実績データの構造化変換を担当します。
"""

import json
import logging
from dataclasses import dataclass
from datetime import date

from openai import OpenAI

logger = logging.getLogger(__name__)

from config.settings import (
    DISH_CATEGORIES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    USER_DIETARY_PREFERENCES,
)


@dataclass
class StructuredDish:
    """構造化された料理データ"""

    dish_name: str
    category: str  # 主菜/副菜/汁物/その他


@dataclass
class GeneratedMenuItem:
    """AIが生成した献立アイテム"""

    date: date
    dish_name: str
    category: str
    shopping_list: str


class OpenAIClientWrapper:
    """
    OpenAI APIとの通信を行うラッパークラス。
    - 実績データの構造化変換
    - 献立の生成
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        クライアントを初期化します。

        Args:
            api_key: OpenAI API キー。省略時は環境変数から取得。
            model: 使用するモデル。省略時は設定から取得。
        """
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model or OPENAI_MODEL

    def structure_raw_input(
        self, raw_text: str, eaten_date: date
    ) -> list[StructuredDish]:
        """
        自由記述の実績を構造化された料理データに変換します。

        Args:
            raw_text: ユーザーの自由記述（例：「キムチ鍋、しめのラーメン」）
            eaten_date: 食べた日付

        Returns:
            構造化された料理データのリスト
        """
        prompt = f"""以下の食事記録を、個別の料理に分解して構造化してください。

# 入力
日付: {eaten_date.isoformat()}
食事記録: {raw_text}

# 出力形式
JSON配列で出力してください。各料理について以下の形式で：
[
  {{
    "dish_name": "料理名",
    "category": "区分"
  }}
]

# 区分の選択肢
- 主菜: メインディッシュ（肉料理、魚料理、メインの一品）
- 副菜: サイドディッシュ（サラダ、和え物、小鉢など）
- 汁物: スープ、味噌汁など
- その他: 上記に当てはまらないもの（デザート、飲み物、軽食など）

# ルール
1. 自由記述から料理を抽出し、適切な区分を割り当てる
2. 「、」「と」などで区切られた複数の料理は個別にリスト化する
3. 「しめのラーメン」のような付随的な料理も独立した1品として扱う
4. 外食や惣菜でも、料理名が特定できれば記録する
5. JSONのみを出力し、説明文は不要

# 出力（JSON配列のみ）
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは食事記録を構造化データに変換する専門家です。JSONのみを出力してください。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return []

        logger.info(f"OpenAI response for structuring: {content}")

        try:
            data = json.loads(content)
            # response_format=json_objectの場合、OpenAIはオブジェクトを返す
            # 可能なキー名: "dishes", "menu", "items", またはルート配列
            if isinstance(data, list):
                dishes_data = data
            else:
                # 様々なキー名に対応（OpenAIは様々なキー名で返す可能性がある）
                dishes_data = (
                    data.get("dishes")
                    or data.get("meals")
                    or data.get("menu")
                    or data.get("items")
                    or data.get("data")
                    or []
                )
                # キーが見つからなかった場合、最初の配列値を探す
                if not dishes_data:
                    for key, value in data.items():
                        if isinstance(value, list):
                            dishes_data = value
                            logger.info(f"Found dishes under key: {key}")
                            break

            logger.debug(f"Extracted dishes_data: {dishes_data}")

            result = []
            for item in dishes_data:
                dish_name = item.get("dish_name", "")
                category = item.get("category", "その他")
                if category not in DISH_CATEGORIES:
                    category = "その他"
                if dish_name:
                    result.append(StructuredDish(dish_name=dish_name, category=category))
            return result
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def generate_weekly_menu(
        self,
        dates_to_fill: list[date],
        existing_plans: list[dict],
        recent_history: list[dict],
        dietary_preferences: str | None = None,
    ) -> list[GeneratedMenuItem]:
        """
        空いている日付の献立を生成します。

        Args:
            dates_to_fill: 献立を生成する日付のリスト
            existing_plans: 既存の予定（確定済み・外食等）
            recent_history: 直近の実績履歴
            dietary_preferences: 食事の好み（省略時は設定から取得）

        Returns:
            生成された献立アイテムのリスト
        """
        if not dates_to_fill:
            return []

        preferences = dietary_preferences or USER_DIETARY_PREFERENCES

        # 既存の予定を文字列化
        existing_str = self._format_existing_plans(existing_plans)

        # 過去の実績を文字列化
        history_str = self._format_history(recent_history)

        # 生成対象の日付を文字列化
        dates_str = ", ".join([d.strftime("%Y-%m-%d (%a)") for d in dates_to_fill])

        prompt = f"""あなたは家庭の献立を考える栄養士です。以下の条件で献立を生成してください。

# 生成対象日
{dates_str}

# ユーザーの好み・要望
{preferences}

# 既存の予定（これらの日は生成不要、重複を避ける参考にしてください）
{existing_str if existing_str else "なし"}

# 直近2週間の食事履歴（重複を避けてください）
{history_str if history_str else "なし"}

# 出力形式
JSON配列で出力してください：
{{
  "menu": [
    {{
      "date": "YYYY-MM-DD",
      "dish_name": "料理名",
      "category": "区分",
      "shopping_list": "必要な食材をカンマ区切りで"
    }}
  ]
}}

# ルール
1. 各日に対して「主菜」「副菜」「汁物」を1品ずつ生成する（計3品/日）
2. メイン食材（鶏肉、豚肉、牛肉、魚など）が2日連続しないようにする
3. 直近の履歴と同じ料理名は避ける
4. 季節感のある食材を取り入れる
5. 買い物リストは具体的な食材名を記載する
6. 調理時間は30分以内で作れるものを優先する

# 出力（JSONのみ）
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは経験豊富な家庭料理の専門家です。バランスの良い献立を提案します。JSONのみを出力してください。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return []

        try:
            data = json.loads(content)
            menu_data = data.get("menu", [])

            result = []
            for item in menu_data:
                date_str = item.get("date", "")
                dish_name = item.get("dish_name", "")
                category = item.get("category", "その他")
                shopping_list = item.get("shopping_list", "")

                if category not in DISH_CATEGORIES:
                    category = "その他"

                if date_str and dish_name:
                    result.append(
                        GeneratedMenuItem(
                            date=date.fromisoformat(date_str),
                            dish_name=dish_name,
                            category=category,
                            shopping_list=shopping_list,
                        )
                    )
            return result
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return []

    def _format_existing_plans(self, plans: list[dict]) -> str:
        """既存の予定をプロンプト用の文字列に整形"""
        if not plans:
            return ""

        lines = []
        for plan in plans:
            date_str = plan.get("date", "")
            dish_name = plan.get("dish_name", "")
            status = plan.get("status", "")
            category = plan.get("category", "")
            lines.append(f"- {date_str}: {dish_name} ({category}) [{status}]")

        return "\n".join(lines)

    def _format_history(self, history: list[dict]) -> str:
        """過去の実績をプロンプト用の文字列に整形"""
        if not history:
            return ""

        lines = []
        for item in history:
            date_str = item.get("date", "")
            dish_name = item.get("dish_name", "")
            category = item.get("category", "")
            lines.append(f"- {date_str}: {dish_name} ({category})")

        return "\n".join(lines)

    def test_connection(self) -> bool:
        """
        OpenAI APIへの接続をテストします。

        Returns:
            接続成功ならTrue
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception:
            return False
