# テスト実行サマリー

> **質問**: Slack通知まで到達するテストは？

**答え**: 3段階のテストレベルがあります。

---

## テストレベルと到達範囲

### Level 1: ユニットテスト ✅ （すぐに実行可能）

**到達範囲:**
- ✅ ロジック正確性
- ✅ データ解析処理
- ❌ 実外部APIコール
- ❌ Slack通知

**実行コマンド:**
```bash
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py
```

**実行時間:** 数秒

**必要な環境変数:** なし

**テストファイル:**
- `test_notion_client.py` - Notionデータ解析
- `test_openai_client.py` - OpenAIレスポンス解析
- `test_menu_generator.py` - 献立生成ロジック
- `test_preprocessor.py` - 実績構造化ロジック

**例:**
```
test_notion_client.py::TestProposedDishParsing::test_parse_proposed_dish_complete PASSED
test_openai_client.py::TestGenerateWeeklyMenu::test_generate_weekly_menu_success PASSED
test_menu_generator.py::TestDateRangeGeneration::test_get_date_range PASSED
```

---

### Level 2: 統合テスト 🔌 （Slack通知を含む）

**到達範囲:**
- ✅ Slack通知送信
- ✅ 実際のWebhook動作
- ✅ メッセージフォーマット
- ❌ Notionへの完全な書き込み
- ❌ OpenAI APIの完全なテスト

**実行コマンド:**
```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
pytest tests/test_integration_slack.py -v
```

**実行時間:** 10秒～1分

**必要な環境変数:**
- `SLACK_WEBHOOK_URL` - Slack Webhook URL

**テストファイル:**
- `test_integration_slack.py` - Slack全通知タイプのテスト

**Slack通知のテスト内容:**
1. ✅ 基本メッセージ送信
2. ✅ 週間献立通知フォーマット
3. ✅ 日次リマインダーフォーマット
4. ✅ エラー通知フォーマット
5. ✅ Webhook接続確認

**実行例:**
```
test_integration_slack.py::TestSlackIntegration::test_send_message_basic PASSED
test_integration_slack.py::TestSlackIntegration::test_send_weekly_menu_notification PASSED
test_integration_slack.py::TestSlackIntegration::test_send_daily_reminder PASSED
test_integration_slack.py::TestSlackIntegration::test_connection PASSED
```

**Slackで確認されるメッセージ例:**

```
🍽️ 今週の献立 (01/15 - 01/21)

*01/15 (月)*
• 主菜: 鶏の唐揚げ ✅
• 副菜: ほうれん草のお浸し 💡
• 汁物: 味噌汁 💡

🛒 買い物リスト
鶏もも肉, ほうれん草, 豆腐, ...
```

---

### Level 3: エンドツーエンドテスト 🚀 （完全フロー）

**到達範囲:**
- ✅ Notion読み書き（実際のデータベース）
- ✅ OpenAI API実行（実績構造化・献立生成）
- ✅ Slack通知送信（実際のメッセージ）
- ✅ 全フロー統合動作

**実行コマンド:**

#### E2E テスト 1: 日次リマインダー完全テスト

```bash
# 環境変数を設定
export NOTION_TOKEN="secret_..."
export DB_ID_PROPOSED="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# テスト実行
pytest tests/test_e2e_daily_reminder.py -v -s
```

**実行時間:** 10秒～1分

**必要な環境変数:**
- `NOTION_TOKEN`
- `DB_ID_PROPOSED`
- `SLACK_WEBHOOK_URL`

**テストフロー:**
1. 今日の献立をNotionから取得
2. Slackにリマインダー送信 ✅ （実際のSlackチャンネルに届く）
3. 指定日付でのテスト
4. 接続確認

#### E2E テスト 2: 週間献立生成完全テスト

```bash
# 環境変数を設定
export NOTION_TOKEN="secret_..."
export DB_ID_PROPOSED="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export DB_ID_RAW="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export DB_ID_STRUCTURED="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export OPENAI_API_KEY="sk-..."
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# テスト実行
pytest tests/test_e2e_weekly_generation.py -v -s
```

**実行時間:** 1～5分

**必要な環境変数:**
- `NOTION_TOKEN`
- `DB_ID_PROPOSED`
- `DB_ID_RAW`
- `DB_ID_STRUCTURED`
- `OPENAI_API_KEY`
- `SLACK_WEBHOOK_URL`

**テストフロー:**
1. 全サービス接続確認
2. 実績データ構造化（OpenAI API使用）
3. 献立生成（OpenAI API使用）✅
4. Notionへ保存
5. Slackへ通知 ✅ （実際のSlackチャンネルに週間献立が届く）

**API使用料:** $0.02～0.06程度

---

## Slack通知が実際に到達するまでの流れ

### ユニットテスト実行時

```
pytest実行
  ↓
モック化されたSlackClientを使用
  ↓
「通知を送った」と判定（実際には何も送られない）
  ↓
テスト完了 ✅
```

### 統合テスト実行時（Slack通知確認可能）

```
pytest実行
  ↓
実際のSlackClientを使用
  ↓
Slack Webhook URLへHTTP POST
  ↓
Slackサーバー受信
  ↓
チャンネルにメッセージ表示 ✅ ← ここで確認可能
  ↓
テスト完了 ✅
```

### E2E テスト実行時（完全フロー確認可能）

```
pytest実行
  ↓
実績データ構造化（OpenAI API実行）
  ↓
献立生成（OpenAI API実行）
  ↓
Notionに保存
  ↓
Slack Webhook URLへHTTP POST
  ↓
Slackサーバー受信
  ↓
チャンネルに献立と買い物リストを表示 ✅ ← ここで確認可能
  ↓
テスト完了 ✅ + コスト発生 ($0.02～0.06)
```

---

## 推奨テスト実行順序

### シナリオ A: 開発中（高速確認）

```bash
# 1. ユニットテストのみ（5秒）
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py
```

### シナリオ B: PR提出前（Slack通知確認）

```bash
# 1. ユニットテスト（5秒）
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py

# 2. Slack統合テスト（1分、Slackチャンネルにテストメッセージが届く）
SLACK_WEBHOOK_URL="your-webhook-url" \
pytest tests/test_integration_slack.py -v -s
```

### シナリオ C: 本番デプロイ前（完全確認）

```bash
# .env ファイルを使用
set -a
source .env
set +a

# 1. ユニットテスト（5秒）
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py

# 2. Slack統合テスト（1分）
pytest tests/test_integration_slack.py -v -s

# 3. 日次リマインダーE2E（1分、実際のNotionとSlackでテスト）
pytest tests/test_e2e_daily_reminder.py -v -s

# 4. 週間献立生成E2E（3～5分、AI使用で費用発生）
pytest tests/test_e2e_weekly_generation.py -v -s
```

---

## 各テストで確認できること

| テストレベル | Slack通知確認 | AI動作確認 | Notion確認 | 実行時間 | コスト |
|-----------|------------|---------|----------|--------|------|
| **ユニット** | ❌ | ❌ | ❌ | 5秒 | 無料 |
| **統合** | ✅ | ❌ | ❌ | 1分 | 無料 |
| **E2E日次** | ✅ | ❌ | ✅ | 1分 | 無料 |
| **E2E週間** | ✅ | ✅ | ✅ | 3-5分 | $0.02～0.06 |

---

## Slack通知テスト時のチェックリスト

### 統合テスト実行後

- [ ] Slackチャンネルに以下のメッセージが届いた
  - [ ] 基本テストメッセージ
  - [ ] 週間献立通知（日付・献立・買い物リスト）
  - [ ] 日次リマインダー（献立と入力リンク）
  - [ ] エラー通知
  - [ ] スキップ通知
  - [ ] 接続テスト完了メッセージ

### E2E 日次テスト実行後

- [ ] Slackチャンネルにリマインダーが届いた
- [ ] メッセージに「今日のご飯はどうでしたか？」が含まれている
- [ ] 献立リストが表示されている
- [ ] Notion実績入力リンクが含まれている

### E2E 週間テスト実行後

- [ ] Slackチャンネルに週間献立が届いた
- [ ] 日付ごとに献立が整理されている
- [ ] 買い物リストが表示されている
- [ ] Notion確認リンクが含まれている
- [ ] Notionの Proposed_Dishes テーブルに新しい献立が追加されている

---

## トラブルシューティング

### 「Slackメッセージが届かない」場合

**ユニットテスト:**
```bash
pytest tests/test_*.py -v --ignore=tests/test_e2e_*.py --ignore=tests/test_integration_*.py
# PASSED が表示されるが、Slackには届かない
# → 正常です（モック化されているため）
```

**統合テスト:**
```bash
SLACK_WEBHOOK_URL="your-webhook-url" \
pytest tests/test_integration_slack.py -v -s
```

**チェック項目:**
- [ ] Webhook URLが正しいか
- [ ] Slackアプリがチャンネルに追加されているか
- [ ] チャンネルが存在しているか
- [ ] チャンネルが非公開になっていないか

### 「OpenAI APIエラー」が出る場合

```
AuthenticationError: Invalid API key
```

- [ ] `OPENAI_API_KEY` が正しいか
- [ ] APIキーに課金が設定されているか
- [ ] APIキーが有効期限内か

### 「Notion接続エラー」が出る場合

```
AssertionError: Notion connection failed
```

- [ ] `NOTION_TOKEN` が正しいか
- [ ] Integrationがデータベースに接続しているか
- [ ] `DB_ID_*` が正しいか

---

## 参考資料

詳細は以下のドキュメントを参照してください：

- [TESTING.md](TESTING.md) - テスト詳細実行ガイド
- [ARCHITECTURE.md](ARCHITECTURE.md) - システムアーキテクチャ
- [README.md](README.md) - セットアップガイド
