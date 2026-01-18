"""
Dinner-Aide 設定ファイル

ユーザーがカスタマイズ可能なパラメータをここに集約します。
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Environment Configuration
# =============================================================================
# ENV: "development" (検証環境) or "production" (本番環境)
# 検証環境ではデータリセット機能が有効になります
ENV = os.getenv("ENV", "development")

def is_development() -> bool:
    """検証環境かどうかを返す"""
    return ENV.lower() in ("development", "dev", "staging", "test")

def is_production() -> bool:
    """本番環境かどうかを返す"""
    return ENV.lower() in ("production", "prod")

# =============================================================================
# Notion API Configuration
# =============================================================================
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")

# Database IDs
DB_ID_PROPOSED = os.getenv("DB_ID_PROPOSED", "")  # 提案メニューテーブル
DB_ID_RAW = os.getenv("DB_ID_RAW", "")  # 実績入力テーブル
DB_ID_STRUCTURED = os.getenv("DB_ID_STRUCTURED", "")  # 実績履歴テーブル

# =============================================================================
# OpenAI API Configuration
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# =============================================================================
# Slack Configuration
# =============================================================================
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# =============================================================================
# User Dietary Preferences (ユーザーの食事の好み・制限)
# =============================================================================
# 環境変数 USER_DIETARY_PREFERENCES から読み取ります。
# 設定されていない場合はデフォルト値（汎用的なサンプル）を使用します。
#
# ⚠️ プライバシーに関わる情報（アレルギー、健康状態、家族構成など）は
#    GitHub Secrets に設定することで、公開リポジトリでも安全に管理できます。
#
# 設定例（.env または GitHub Secrets）:
#   USER_DIETARY_PREFERENCES="- 野菜を多めに\n- 調理時間は30分以内"
#
# 改行は \n で表現してください。
_DEFAULT_DIETARY_PREFERENCES = """
- 野菜を毎食必ず1品は入れる
- できるだけ季節の食材を使う
- 調理時間は30分以内で作れるものが望ましい
- バランスの良い献立を心がける
"""

# 環境変数から取得（改行文字 \n を実際の改行に変換）
_raw_preferences = os.getenv("USER_DIETARY_PREFERENCES", "")
if _raw_preferences:
    # \n を実際の改行に変換
    USER_DIETARY_PREFERENCES = _raw_preferences.replace("\\n", "\n")
else:
    USER_DIETARY_PREFERENCES = _DEFAULT_DIETARY_PREFERENCES

# =============================================================================
# Menu Generation Settings
# =============================================================================
# 献立を生成する曜日の範囲（月曜日=0, 日曜日=6）
WEEK_START_DAY = 0  # 月曜日
WEEK_END_DAY = 6  # 日曜日

# 過去の実績を何週間分参照するか
HISTORY_WEEKS = 2

# 1日あたりの献立構成
DAILY_MENU_STRUCTURE = {
    "主菜": 1,  # 1品
    "副菜": 1,  # 1品
    "汁物": 1,  # 1品（任意）
}

# =============================================================================
# Category Definitions (区分の定義)
# =============================================================================
DISH_CATEGORIES = ["主菜", "副菜", "汁物", "その他"]

# =============================================================================
# Status Definitions (ステータスの定義)
# =============================================================================
DISH_STATUSES = ["提案", "確定", "外食・予定あり"]

# =============================================================================
# Validation
# =============================================================================
def validate_config() -> list[str]:
    """
    設定の妥当性を検証し、エラーメッセージのリストを返す。
    空リストが返れば設定は有効。
    """
    errors = []

    if not NOTION_TOKEN:
        errors.append("NOTION_TOKEN is not set")

    if not DB_ID_PROPOSED:
        errors.append("DB_ID_PROPOSED is not set")

    if not DB_ID_RAW:
        errors.append("DB_ID_RAW is not set")

    if not DB_ID_STRUCTURED:
        errors.append("DB_ID_STRUCTURED is not set")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set")

    if not SLACK_WEBHOOK_URL:
        errors.append("SLACK_WEBHOOK_URL is not set")

    return errors
