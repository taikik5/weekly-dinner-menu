# テスト実行ガイド

Dinner-Aideのテストは3つのレベルに分かれています。

## テストの3段階

### 1. ユニットテスト（Unit Tests）✅ すぐに実行可能

**特徴:**
- 環境変数不要
- API呼び出しなし（すべてモック化）
- 実行速度が速い（数秒）
- 到達範囲：ロジックの正確性確認

**実行方法:**
```bash
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py
```

または、特定のテストファイルだけ実行：
```bash
pytest tests/test_notion_client.py -v
pytest tests/test_openai_client.py -v
pytest tests/test_menu_generator.py -v
pytest tests/test_preprocessor.py -v
```

**テスト内容:**
- `test_notion_client.py`: Notionクライアントのパース処理
- `test_openai_client.py`: OpenAIクライアントのレスポンス処理
- `test_menu_generator.py`: 献立生成ロジック（日付計算など）
- `test_preprocessor.py`: 実績データ構造化ロジック

---

### 2. 統合テスト（Integration Tests）🔌 API呼び出し検証

**特徴:**
- Slack Webhook URLが必要
- 実際のSlackへ通知を送信
- OpenAI/Notionへのモック使用
- 実行速度：中程度（数秒～数十秒）

**実行方法:**
```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." \
pytest tests/test_integration_slack.py -v
```

**前提条件:**
1. Slack Webhook URLを準備
2. 通知が届くSlackチャンネルを確認

**テスト内容:**
- 基本メッセージ送信
- 週間献立通知フォーマット
- 日次リマインダーフォーマット
- エラー通知フォーマット
- Slack接続確認

---

### 3. エンドツーエンドテスト（E2E Tests）🚀 完全フロー検証

**特徴:**
- すべての環境変数が必要
- 実際のNotionからデータを取得
- 実際のOpenAI APIを呼び出し（**費用発生**）
- 実際のSlackに通知を送信
- 実行速度：遅い（1～5分程度）

#### E2E テスト 1: 日次リマインダーフロー

```bash
NOTION_TOKEN="secret_..." \
DB_ID_PROPOSED="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
SLACK_WEBHOOK_URL="https://hooks.slack.com/..." \
pytest tests/test_e2e_daily_reminder.py -v -s
```

**前提条件:**
- Notionの提案メニューテーブル（DB_ID_PROPOSED）が設定済み
- 今日のデータが入っている（またはテスト用データを作成）

**テスト内容:**
- 今日の献立をNotionから取得
- Slackにリマインダーを送信
- 指定日付でのリマインダー送信
- Notion/Slack接続確認

**実行例:**

```bash
# .env ファイルから読み込む場合
set -a
source .env
set +a
pytest tests/test_e2e_daily_reminder.py -v -s
```

#### E2E テスト 2: 週間献立生成フロー

```bash
NOTION_TOKEN="secret_..." \
DB_ID_PROPOSED="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
DB_ID_RAW="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
DB_ID_STRUCTURED="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
OPENAI_API_KEY="sk-..." \
SLACK_WEBHOOK_URL="https://hooks.slack.com/..." \
pytest tests/test_e2e_weekly_generation.py -v -s
```

**前提条件:**
- Notionの全3テーブルが設定済み
- OpenAI APIの課金設定が完了
- テスト用のデータを準備（推奨）

**テスト内容:**
1. **全サービス接続テスト**: Notion/OpenAI/Slack接続確認
2. **プリプロセッシング**: Raw_Actual_Input の処理
3. **献立生成**: 次週の献立生成と保存
4. **完全フロー**: 上記の全フローを実行

---

## 実行方法のまとめ

### シナリオ 1: とにかく早く確認したい

```bash
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py
```

所要時間: 数秒

---

### シナリオ 2: Slack通知まで確認したい

```bash
# 1. ユニットテスト実行
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py

# 2. Slack統合テスト実行
SLACK_WEBHOOK_URL="your-webhook-url" \
pytest tests/test_integration_slack.py -v
```

所要時間: 10秒～1分

---

### シナリオ 3: 完全な動作確認（本番前）

```bash
# .env ファイルから環境変数を読み込み
set -a
source .env
set +a

# 1. ユニットテスト
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py

# 2. Slack統合テスト
pytest tests/test_integration_slack.py -v -s

# 3. E2E テスト（日次リマインダー）
pytest tests/test_e2e_daily_reminder.py -v -s

# 4. E2E テスト（週間献立生成）
pytest tests/test_e2e_weekly_generation.py -v -s
```

所要時間: 数分～10分（OpenAI APIの速度に依存）

---

### シナリオ 4: 特定のテストだけ実行

```bash
# Notionクライアントのテストだけ
pytest tests/test_notion_client.py -v

# 日次リマインダーのE2Eテストだけ
NOTION_TOKEN="..." DB_ID_PROPOSED="..." SLACK_WEBHOOK_URL="..." \
pytest tests/test_e2e_daily_reminder.py::TestDailyReminderE2E::test_send_daily_reminder_today -v -s
```

---

## ログ出力の表示

E2E テストでログを確認したい場合は `-s` フラグを使用：

```bash
pytest tests/test_e2e_weekly_generation.py -v -s
```

出力例:
```
Testing all service connections...
  • Testing Notion connection...
    ✓ Notion connection successful
  • Testing OpenAI connection...
    ✓ OpenAI connection successful
  • Testing Slack connection...
    ✓ Slack connection successful
```

---

## トラブルシューティング

### モジュール不足エラー

```
ModuleNotFoundError: No module named 'notion_client'
```

**解決方法:**
```bash
pip install -r requirements.txt
```

### 環境変数エラー

```
SKIP: Missing environment variables: SLACK_WEBHOOK_URL
```

**解決方法:**
```bash
export SLACK_WEBHOOK_URL="your-webhook-url"
pytest tests/test_integration_slack.py -v
```

または `.env` ファイルを使用：
```bash
set -a
source .env
set +a
pytest tests/test_integration_slack.py -v
```

### Notion接続エラー

```
AssertionError: Notion connection failed
```

**チェック項目:**
- `NOTION_TOKEN` が正しいか
- `DB_ID_*` が正しいか
- Integrationがデータベースに接続しているか

### OpenAI エラー

```
AuthenticationError: Invalid API key
```

**チェック項目:**
- `OPENAI_API_KEY` が正しいか
- APIキーに課金設定がされているか

### Slack エラー

```
AssertionError: Slack connection failed
```

**チェック項目:**
- Webhook URLが正しいか
- チャンネルが削除されていないか

---

## CI/CD での使用

GitHub Actions でテストを自動実行する場合：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -r requirements.txt

      # ユニットテスト（常に実行）
      - run: pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py

      # E2Eテスト（nightlyなど定期実行）
      - name: Run E2E tests
        if: github.event_name == 'schedule'
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          DB_ID_PROPOSED: ${{ secrets.DB_ID_PROPOSED }}
          # ... その他の環境変数
        run: pytest tests/test_e2e_*.py -v
```

---

## 推奨テスト戦略

1. **開発中**: ユニットテストのみ（高速）
2. **PR提出前**: ユニット + Slack統合テスト
3. **本番デプロイ前**: 全テスト（E2E含む）
4. **定期実行**: E2Eテストをweeklyで実行

---

## コスト管理

### OpenAI API コスト

E2Eテストを実行すると、OpenAI APIへのコールが発生します。

**1回のテスト実行あたりの概算コスト:**
- 実績構造化: $0.001 ～ $0.01
- 献立生成: $0.01 ～ $0.05
- **合計: $0.02 ～ $0.06 程度**

頻繁にE2Eテストを実行する場合は、`test_e2e_weekly_generation.py::TestWeeklyGenerationE2E::test_all_connections` だけ実行することで、APIコストを抑えられます。

---

## 参考資料

- [pytest ドキュメント](https://docs.pytest.org/)
- [unittest.mock ドキュメント](https://docs.python.org/3/library/unittest.mock.html)
- [Notion API](https://developers.notion.com/)
- [OpenAI API](https://platform.openai.com/docs/)
- [Slack Webhooks](https://api.slack.com/messaging/webhooks)
