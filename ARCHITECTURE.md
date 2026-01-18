# Dinner-Aide アーキテクチャドキュメント

## システム概要

Dinner-Aideは、以下の3つのコンポーネントを組み合わせた献立管理システムです。

```
┌─────────────────────────────────────────────────────────────────┐
│                        Dinner-Aide System                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Notion     │         │  OpenAI API  │         │  Slack       │
│  (Database)  │         │  (AI Engine) │         │  (Interface) │
└──────────────┘         └──────────────┘         └──────────────┘
       ▲                        ▲                        ▲
       │                        │                        │
       └────────────┬───────────┴────────────┬──────────┘
                    │                        │
            ┌───────▼────────────────────────▼────────┐
            │    Dinner-Aide Core Logic               │
            │  (Python 3.10+)                         │
            └───────┬────────────────────────┬────────┘
                    │                        │
         ┌──────────▼─┐            ┌────────▼──────────┐
         │ 2 Workflows│            │  3 Data Tables    │
         │ (Automated)│            │  (Notion)         │
         └────────────┘            └───────────────────┘
```

---

## コンポーネント構成

### 1. ユーザーインターフェース層

| ツール | 役割 | 使用頻度 |
|--------|------|---------|
| **Notion** | 献立の確認・編集、実績の記録 | 毎日 |
| **Slack** | 献立提案・実績リマインダーの受け取り | 毎日 |
| **GitHub** | 環境設定、ワークフロー管理 | 月1～2回 |

### 2. コア処理層（Python）

```
src/
├── main.py                    # エントリーポイント
├── notion_client.py           # Notion API ラッパー
├── openai_client.py           # OpenAI API ラッパー
├── slack_client.py            # Slack Webhook ラッパー
├── preprocessor.py            # 実績データ構造化エンジン
├── menu_generator.py          # 献立生成エンジン
└── daily_reminder.py          # リマインダー送信エンジン

config/
└── settings.py                # ユーザー設定（食事の好みなど）
```

### 3. データ層（Notion データベース）

| テーブル | 役割 | 入力者 | 更新者 |
|---------|------|--------|--------|
| **Proposed_Dishes** | 献立提案・確定・外食予定の管理 | AI/ユーザー | ユーザー |
| **Raw_Actual_Input** | 食べたものの自由記述 | ユーザー | ユーザー |
| **Structured_Actual_History** | 構造化済み実績のみ保存 | システム | - |

---

## 実行フロー

### フロー 1: 週間献立生成（毎週土曜日 06:00 JST）

```
Step 1: 実績データの構造化（前夜の実績を処理）
  Raw_Actual_Input (未処理)
    ↓
  [OpenAI: 自由記述を分解・分類]
    ↓
  Structured_Actual_History (保存)
  + Raw_Actual_Input (処理済みにマーク)

Step 2: 既存予定の確認
  Proposed_Dishes (次週の確定・外食予定を抽出)
    ↓
  [空枠を特定]
    ↓
  生成対象日リスト

Step 3: AI献立生成
  [Context]
  - ユーザー食事の好み（設定）
  - 既存予定
  - 過去2週間の実績
    ↓
  [OpenAI: 献立を生成]
    ↓
  生成された献立

Step 4: Notionに保存 & Slack通知
  生成献立 → Proposed_Dishes (ステータス: 提案)
  献立リスト → Slack (通知)
```

**処理時間:** 2～3分
**コスト:** $0.01～$0.05
**失敗時:** エラー通知をSlackに送信

### フロー 2: 日次実績リマインダー（毎日 19:00 JST）

```
Step 1: 今日の献立を取得
  Proposed_Dishes (今日の日付)
    ↓
  [絞り込み]
    ↓
  今日の献立リスト

Step 2: リマインダー送成
  [フォーマット]
  - 献立の内容を表示
  - 実績入力用Notionリンク
    ↓
  Slack にリマインダー送信
```

**処理時間:** 数秒
**コスト:** 無料（Notion/Slack読み取りのみ）
**失敗時:** エラー通知をSlackに送信

---

## クライアント実装詳細

### NotionClientWrapper (`src/notion_client.py`)

**責務:**
- Notionの3つのテーブルへのCRUD操作
- ページデータの解析とPythonオブジェクトへの変換
- データベースURLの生成

**主要メソッド:**

| メソッド | 操作 | 対象テーブル |
|---------|------|------------|
| `get_proposed_dishes_by_date_range()` | 読 | Proposed_Dishes |
| `get_proposed_dishes_by_date()` | 読 | Proposed_Dishes |
| `create_proposed_dish()` | 書 | Proposed_Dishes |
| `update_proposed_dish_status()` | 更 | Proposed_Dishes |
| `get_unprocessed_raw_inputs()` | 読 | Raw_Actual_Input |
| `mark_raw_input_as_processed()` | 更 | Raw_Actual_Input |
| `get_structured_history_by_date_range()` | 読 | Structured_Actual_History |
| `create_structured_history()` | 書 | Structured_Actual_History |

**エラーハンドリング:**
- API接続エラー: 例外を発生
- 無効なデータベースID: 例外を発生
- データ不在: 空のリストを返却

### OpenAIClientWrapper (`src/openai_client.py`)

**責務:**
- OpenAI APIへのプロンプト送信
- JSON形式のレスポンス解析
- 構造化変換と献立生成の2つのプロンプト管理

**主要メソッド:**

| メソッド | 処理 | コスト | 時間 |
|---------|------|--------|------|
| `structure_raw_input()` | 自由記述を構造化 | ~$0.001 | ~1秒 |
| `generate_weekly_menu()` | 献立を生成 | ~$0.01-0.05 | ~10秒 |

**プロンプト戦略:**
1. **構造化プロンプト**: 低温度（temperature=0.3）で確定的な結果
2. **献立生成プロンプト**: 中温度（temperature=0.7）で創造的な結果

**エラーハンドリング:**
- 無効なAPIキー: 例外を発生
- JSON解析失敗: 空のリストを返却
- レート制限: 自動再試行（実装待ち）

### SlackClientWrapper (`src/slack_client.py`)

**責務:**
- Slack Webhookを使用したメッセージ送信
- Block Kit形式での見やすいフォーマット
- 複数の通知タイプ対応

**主要メソッド:**

| メソッド | 用途 |
|---------|------|
| `send_message()` | 基本メッセージ送信 |
| `send_weekly_menu_notification()` | 週間献立通知 |
| `send_daily_reminder()` | 日次リマインダー |
| `send_error_notification()` | エラー通知 |
| `send_skip_notification()` | スキップ理由通知 |

**フォーマット例:**

```
🍽️ 今週の献立 (01/15 - 01/21)

*01/15 (月)*
• 主菜: 鶏の唐揚げ ✅
• 副菜: ほうれん草のお浸し 💡
• 汁物: 味噌汁 💡

🛒 買い物リスト
鶏もも肉, ほうれん草, 豆腐, ...

📝 Notionで確認・編集する
```

**エラーハンドリング:**
- 無効なWebhook URL: 例外を発生
- ネットワーク錯誤: False返却

---

## ビジネスロジック

### ActualDataPreprocessor (`src/preprocessor.py`)

**目的:** Raw_Actual_Input → Structured_Actual_History の自動変換

**処理ステップ:**

1. 未処理のレコードを取得
2. 空のレコードをスキップ
3. OpenAI APIで構造化
4. 構造化データをテーブルに保存
5. 元のレコードを「処理済み」にマーク

**例外処理:**
- API呼び出し失敗時も続行（部分的な成功を許容）
- 空のレスポンスはスキップ

### WeeklyMenuGenerator (`src/menu_generator.py`)

**目的:** 空いている日付の献立を自動生成

**キーロジック: 「差分生成」**

```python
# 生成対象日 = 全日 - 確定済み日付
dates_to_fill = all_dates - dates_with_confirmed_plans

# 既存予定と重複するメイン食材は避ける
# (AIのプロンプトで指示)
```

**処理ステップ:**

1. 次週の週頭・週末を計算
2. 既存の「確定」「外食」予定を抽出
3. 空きを特定
4. 空きがない → スキップ通知
5. 過去2週間の実績を取得
6. OpenAI APIで献立を生成
7. Notionに保存
8. Slackに通知

**特殊ロジック:**

```python
# 曜日の計算（毎週土曜がトリガー）
def _get_next_week_range(self, reference_date):
    """次の月曜～日曜を返す"""
    days_until_monday = (7 - reference_date.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return next_monday, next_sunday
```

### DailyReminderSender (`src/daily_reminder.py`)

**目的:** 毎日19:00に実績記録のリマインダーを送信

**処理ステップ:**

1. 今日の献立を取得
2. Slackにリマインダーを送信

**特徴:**
- 献立がない日も通知（記録忘れ防止）
- 予定と実績の差分確認を促す

---

## テスト戦略

### テストの3層

```
Layer 3: E2E Tests (統合テスト)
  └─ 実際のNotion/OpenAI/Slackを使用
     └─ ロジック全体の動作確認

Layer 2: Integration Tests (API統合テスト)
  └─ 実際のSlack Webhookを使用
     └─ 外部API呼び出しの確認

Layer 1: Unit Tests (単体テスト)
  └─ モック化されたテスト
     └─ ロジックの正確性確認
```

### ユニットテストの対象

| ファイル | テスト対象 |
|---------|----------|
| `test_notion_client.py` | ページデータの解析 |
| `test_openai_client.py` | JSONレスポンスの解析 |
| `test_menu_generator.py` | 日付計算・ロジック |
| `test_preprocessor.py` | データ処理フロー |

### E2E テストの対象

| ファイル | テスト内容 |
|---------|----------|
| `test_e2e_daily_reminder.py` | 日次リマインダー完全フロー |
| `test_e2e_weekly_generation.py` | 週間献立生成完全フロー |

---

## デプロイメント

### GitHub Actions ワークフロー

#### `weekly-menu.yml`
- **トリガー:** 毎週土曜日 06:00 JST
- **処理:** 週間献立生成フロー（Step 1-3）
- **時間:** 2～3分
- **コスト:** $0.02～$0.06

#### `daily-reminder.yml`
- **トリガー:** 毎日 19:00 JST
- **処理:** 日次リマインダー送信
- **時間:** 数秒
- **コスト:** 無料

### 環境変数（シークレット）

| シークレット名 | 説明 |
|-------------|------|
| `NOTION_TOKEN` | Notion Integration トークン |
| `DB_ID_PROPOSED` | 提案メニューテーブルID |
| `DB_ID_RAW` | 実績入力テーブルID |
| `DB_ID_STRUCTURED` | 実績履歴テーブルID |
| `OPENAI_API_KEY` | OpenAI APIキー |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL |

---

## パフォーマンス特性

### 処理時間

| 処理 | 所要時間 | ボトルネック |
|-----|---------|----------|
| 実績構造化（1件） | 1～5秒 | OpenAI API |
| 献立生成（1週間） | 10～20秒 | OpenAI API |
| 日次リマインダー | 1～2秒 | Notion読み取り |
| 全フロー | 2～3分 | OpenAI API |

### API コスト（月額概算）

| サービス | 月額 | 内訳 |
|---------|------|------|
| **Notion** | 無料 | 読み取り/書き込み制限なし |
| **OpenAI** | $1～3 | 週1回の献立生成 + 実績構造化 |
| **Slack** | 無料 | Webhook制限なし |
| **GitHub** | 無料 | Actions制限: 2,000分/月 |

---

## スケーラビリティ

### 現在の制限

| 項目 | 制限値 | 対応 |
|-----|--------|------|
| 1週間の献立数 | 最大21品（3品/日 × 7日） | OK |
| 過去実績参照期間 | 2週間固定 | 設定で変更可 |
| 献立生成頻度 | 週1回 | 十分 |

### 今後の改善案

- [ ] 実績データの長期参照（月単位）
- [ ] 機械学習による好み学習
- [ ] ユーザーごとの献立カスタマイズ
- [ ] 複数ユーザー対応
- [ ] 家族単位での献立管理

---

## セキュリティ考慮事項

### APIキー管理

- ✅ GitHub Secrets で管理
- ✅ `.env` ファイルは `.gitignore` に含める
- ✅ ログにキーを出力しない

### データプライバシー

- ✅ Notionデータはユーザーのアカウント配下
- ✅ OpenAIへはテンプレートとユーザー記述のみ送信（個人情報送信に注意）
- ✅ Slackメッセージはチャンネルメンバーのみ表示

---

## トラブルシューティング

### よくあるエラー

| エラー | 原因 | 対応 |
|-------|------|------|
| `Authentication Error` | Notion/OpenAI トークン無効 | 再発行 |
| `Rate Limit Exceeded` | OpenAI APIレート制限 | 待機・アップグレード |
| `Invalid Webhook URL` | Slack URL無効 | URL再確認 |
| `Empty Response` | OpenAIが空を返す | プロンプト調整 |

詳細は [TESTING.md](TESTING.md) の「トラブルシューティング」を参照

---

## 今後の開発ロードマップ

### Phase 1: 基本機能（現在）
- ✅ 週間献立自動生成
- ✅ 日次リマインダー
- ✅ 実績データ構造化

### Phase 2: 改善（Q2）
- [ ] キャッシング機能（重複生成防止）
- [ ] 予算機能（食材コスト管理）
- [ ] レシピリンク統合

### Phase 3: 拡張（Q3）
- [ ] 複数ユーザー対応
- [ ] 栄養管理
- [ ] アレルギー対応

### Phase 4: AI強化（Q4）
- [ ] ファインチューニング
- [ ] ユーザー好み学習
- [ ] リアルタイム提案

---

## 参考リソース

- [Notion API ドキュメント](https://developers.notion.com/)
- [OpenAI API ドキュメント](https://platform.openai.com/docs/)
- [Slack Webhooks](https://api.slack.com/messaging/webhooks)
- [GitHub Actions](https://github.com/features/actions)
