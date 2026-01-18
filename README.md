# Dinner-Aide - 献立自動生成・管理システム

NotionをメインDB、OpenAI APIを思考エンジン、Slackをインターフェースとして、家庭の献立管理を自動化するツールです。

## 機能概要

- **週間献立の自動生成**: 毎週土曜日 6:00 に次週の献立を自動生成
- **既存予定の尊重**: Notionに手動入力した予定（外食等）を考慮
- **飽きない提案**: 過去2週間の実績を参照し、重複を避けた献立を提案
- **買い物リストの自動生成**: 献立に必要な食材を自動でリスト化
- **日次リマインダー**: 毎日19:00に実績入力のリマインドを送信（未処理の実績データも自動構造化）

## クイックスタート

### 1. 事前準備

以下の3つのサービスの設定が必要です：

1. **Notion API**
2. **OpenAI API**
3. **Slack Webhook**

---

## Notion データベースの準備

Notionで以下の3つのデータベースを作成してください。

### ① 提案メニューテーブル (`Proposed_Dishes`)

システムが献立を提案・保存するテーブルです。

| プロパティ名 | 型 | 設定内容 |
|------------|------|---------|
| **料理名** | Title | デフォルトのまま |
| **日付** | Date | デフォルトのまま |
| **区分** | Select | 選択肢: `主菜`, `副菜`, `汁物`, `その他` |
| **ステータス** | Select | 選択肢: `提案`, `確定`, `外食・予定あり` |
| **買い物リスト** | Text | デフォルトのまま |

**使い方:**
- AIが生成した献立は「提案」ステータスで保存されます
- 確定したい献立は「確定」に変更してください
- 外食予定や手動で入力した予定は「外食・予定あり」を選択してください

### ② 実績入力テーブル (`Raw_Actual_Input`)

日々の食事を自由記述で入力するテーブルです。

| プロパティ名 | 型 | 設定内容 |
|------------|------|---------|
| **食べたもの** | Title | デフォルトのまま |
| **日付** | Date | デフォルトのまま |
| **処理済み** | Checkbox | デフォルトのまま |

**使い方:**
- 「食べたもの」に自由に記述してください（例：「キムチ鍋、しめのラーメン」）
- システムが自動で構造化データに変換し、「処理済み」にチェックを入れます

### ③ 実績履歴テーブル (`Structured_Actual_History`)

システムが構造化した実績を保存するテーブルです。手動での入力は不要です。

| プロパティ名 | 型 | 設定内容 |
|------------|------|---------|
| **料理名** | Title | デフォルトのまま |
| **日付** | Date | デフォルトのまま |
| **区分** | Select | 選択肢: `主菜`, `副菜`, `汁物`, `その他` |

---

## Notion Integration の作成

1. [Notion Developers](https://www.notion.so/my-integrations) にアクセス
2. 「新しいインテグレーション」をクリック
3. 名前を入力（例：`Dinner-Aide`）
4. 関連ワークスペースを選択
5. 機能は以下を有効化：
   - コンテンツを読み取る
   - コンテンツを挿入する
   - コンテンツを更新する
6. 「送信」をクリック
7. 表示される「内部インテグレーショントークン」をコピー（`secret_xxxx...` の形式）

### データベースへの接続

作成した3つのデータベースそれぞれで：

1. データベースを開く
2. 右上の「...」メニューをクリック
3. 「接続」→ 作成したインテグレーション名を選択

### データベースIDの取得

各データベースのURLからIDを取得します：

```
https://www.notion.so/your-workspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                     この部分がデータベースID（32文字）
```

---

## OpenAI API の準備

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. ログインまたはアカウント作成
3. 左メニューの「API keys」をクリック
4. 「Create new secret key」をクリック
5. 表示されるAPIキーをコピー（`sk-xxxx...` の形式）

**注意:** APIキーは一度しか表示されません。必ず安全な場所に保存してください。

---

## Slack Webhook の準備

1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」→「From scratch」を選択
3. アプリ名とワークスペースを設定
4. 左メニューの「Incoming Webhooks」をクリック
5. 「Activate Incoming Webhooks」をONに
6. 「Add New Webhook to Workspace」をクリック
7. 通知を送信するチャンネルを選択
8. 表示されるWebhook URLをコピー（`https://hooks.slack.com/services/...` の形式）

---

## 環境変数の設定

### ローカル実行の場合

プロジェクトルートに `.env` ファイルを作成：

```bash
cp .env.example .env
```

`.env` を編集して値を設定：

```env
# Notion API
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Notion Database IDs
DB_ID_PROPOSED=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_ID_RAW=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DB_ID_STRUCTURED=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Slack Webhook URL
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### GitHub Actions の場合

リポジトリの Settings → Secrets and variables → Actions で以下のシークレットを設定：

| シークレット名 | 必須 | 説明 |
|--------------|:----:|------|
| `NOTION_TOKEN` | ✅ | Notion Integration トークン |
| `DB_ID_PROPOSED` | ✅ | 提案メニューテーブルのID |
| `DB_ID_RAW` | ✅ | 実績入力テーブルのID |
| `DB_ID_STRUCTURED` | ✅ | 実績履歴テーブルのID |
| `OPENAI_API_KEY` | ✅ | OpenAI APIキー |
| `SLACK_WEBHOOK_URL` | ✅ | Slack Webhook URL |
| `USER_DIETARY_PREFERENCES` | - | 食事の好み・制限（プライベート情報用、下記参照） |

#### プライベートな食事の好み・制限を設定する

アレルギー、健康状態、家族構成などのプライバシーに関わる情報は、公開リポジトリのコードに直接書かずに **GitHub Secrets** で管理できます。

**設定例**（`USER_DIETARY_PREFERENCES` シークレットに登録）：
```
- 生魚・生肉は避ける\n- 子供が食べやすい味付けにする\n- 辛いものは控える\n- 調理時間は30分以内
```

**注意点**：
- 改行は `\n` で表現してください
- 設定しない場合はデフォルトの汎用的な好みが使用されます
- ローカル実行時は `.env` ファイルに記載します（`.env` は `.gitignore` で除外済み）

---

## インストールと実行

### 仮想環境の作成

Pythonの依存関係を分離するため、仮想環境を作成することを推奨します：

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
# macOS/Linux の場合
source venv/bin/activate

# Windows の場合
venv\Scripts\activate
```

仮想環境が有効化されると、ターミナルのプロンプトに `(venv)` が表示されます。

### ローカルでの実行

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 接続テスト
python -m src.main test

# 週間献立生成（手動実行）
python -m src.main weekly

# 日次リマインダー（手動実行）
python -m src.main daily
```

### GitHub Actions での自動実行

リポジトリにpushすると、以下のスケジュールで自動実行されます：

| ワークフロー | スケジュール | 説明 |
|------------|------------|------|
| **Weekly Menu Generation** | 毎週土曜日 06:00 (JST) | 次週の献立を自動生成してSlackに通知 |
| **Daily Reminder** | 毎日 19:00 (JST) | 今日の予定メニューを表示し、実績入力をリマインド |
| **Test Full Cycle** | 手動実行のみ | テスト用: データリセット→テストデータ投入→献立生成→リマインダー送信 |

#### 手動実行

1. GitHub リポジトリの「Actions」タブ
2. 左メニューから実行したいワークフローを選択
3. 「Run workflow」をクリック

#### テスト用ワークフロー（Test Full Cycle）

システム全体の動作確認やテスト時に使用します。**データベースの全データが削除される**ため、テスト専用のデータベースでの使用を推奨します。

```
実行される処理:
1. データベースリセット（全テーブルのデータを削除）
2. テストデータ投入（サンプル実績データ4件）
3. 週間献立生成（AIで献立を生成してSlack通知）
4. 日次リマインダー送信（今日の献立をSlack通知）
```

**実行方法**:
1. Actions タブ → 「Test Full Cycle (Development Only)」を選択
2. 「Run workflow」をクリック
3. `reset_data` オプションを選択（デフォルト: `all`）
   - `all`: 全テーブルをリセット
   - `proposed`: 提案メニューテーブルのみ
   - `raw`: 実績入力テーブルのみ
   - `structured`: 実績履歴テーブルのみ

詳細な設定方法は [GITHUB_SETUP.md](GITHUB_SETUP.md) を参照してください。

---

## 食事の好みをカスタマイズ

献立生成時に考慮される好み・制限を設定できます。設定方法は 2 通りあります。

### 方法 1: 環境変数で設定（推奨）

プライバシーに関わる情報（アレルギー、健康状態、家族構成など）を含む場合はこちらを推奨します。

**ローカル実行の場合**（`.env` ファイル）：
```bash
# .env ファイルに追加
USER_DIETARY_PREFERENCES="- 生魚・生肉は避ける\n- 塩分控えめ\n- グルテンフリー"
```

**GitHub Actions の場合**（GitHub Secrets）：
1. Settings → Secrets and variables → Actions
2. `USER_DIETARY_PREFERENCES` という名前で登録
3. 改行は `\n` で表現

### 方法 2: 設定ファイルを直接編集

汎用的な好み（公開しても問題ない内容）の場合は、`config/settings.py` の `_DEFAULT_DIETARY_PREFERENCES` を編集できます。

```python
_DEFAULT_DIETARY_PREFERENCES = """
- 野菜を毎食必ず1品は入れる
- できるだけ季節の食材を使う
- 調理時間は30分以内で作れるものが望ましい
- バランスの良い献立を心がける
"""
```

**優先順位**: 環境変数 `USER_DIETARY_PREFERENCES` が設定されている場合はそちらが優先されます。

---

## 使い方ガイド

### 週間の流れ

1. **土曜日 06:00**: システムが次週（月〜日）の献立を自動生成
2. **Slackに通知**: 週間献立と買い物リストが送信される
3. **Notionで確認・編集**: 必要に応じて献立を変更
4. **毎日 19:00**: 実績入力のリマインダーがSlackに届く
5. **Notionに実績入力**: 「実績入力テーブル」に食べたものを記録

### 予定を先に入れておく場合

外食予定などがある場合は、事前にNotionの「提案メニューテーブル」に入力しておくと、その日はスキップされます。

1. 「提案メニューテーブル」を開く
2. 新規レコードを作成
3. 日付を設定
4. 料理名（例：「外食」「実家で食事」など）を入力
5. ステータスを「外食・予定あり」に設定

---

## 検証環境での開発・テスト

### 環境変数 `ENV` の設定

本システムは `ENV` 環境変数で検証環境と本番環境を切り替えます。

| ENV値 | 環境 | データリセット機能 |
|-------|------|-------------------|
| `development` (デフォルト) | 検証環境 | ✅ 有効 |
| `dev`, `staging`, `test` | 検証環境 | ✅ 有効 |
| `production`, `prod` | 本番環境 | ❌ ブロック |

```bash
# .env ファイルに追加
ENV=development  # 検証環境（デフォルト）
# ENV=production  # 本番環境（データリセット機能が無効化）
```

### データベースのリセット（検証環境専用）

テストの度にデータをクリアしたい場合に使用します。

```bash
# 全テーブルをリセット（確認あり）
python -m src.main reset

# 全テーブルをリセット（確認なし）
python -m src.main reset --force

# 特定のテーブルのみリセット
python -m src.main reset --tables proposed          # 提案メニューのみ
python -m src.main reset --tables raw               # 実績入力のみ
python -m src.main reset --tables structured        # 実績履歴のみ
python -m src.main reset --tables proposed raw      # 複数指定
```

**⚠️ 注意**: `ENV=production` の場合、リセットコマンドは実行がブロックされます。

### テストデータの投入（検証環境専用）

`Raw_Actual_Input` テーブルにサンプルデータを投入します。

```bash
python -m src.main seed
```

投入されるデータ例:
- 3日前: 「キムチ鍋、しめのラーメン」
- 2日前: 「焼き魚、ほうれん草のおひたし、味噌汁」
- 1日前: 「カレーライス、サラダ」
- 今日: 「鶏の唐揚げ、ポテトサラダ、わかめスープ」

### 検証フロー（推奨手順）

以下の手順で3つのデータベースの動作を検証できます。

#### ステップ 1: データリセット

```bash
python -m src.main reset --force
```

#### ステップ 2: テストデータ投入

```bash
python -m src.main seed
```

→ **確認**: Notion の `Raw_Actual_Input` テーブルに4件のデータが作成される

#### ステップ 3: 週間献立生成を実行

```bash
python -m src.main weekly
```

このコマンドは以下を実行します:

1. **実績データの構造化** (`Raw_Actual_Input` → `Structured_Actual_History`)
   - `Raw_Actual_Input` の「処理済み」が `true` に更新される
   - `Structured_Actual_History` に構造化されたデータが作成される

2. **週間献立の生成** (AI → `Proposed_Dishes`)
   - 次週分の献立が `Proposed_Dishes` に作成される
   - Slack に週間献立が通知される

→ **確認ポイント**:
- `Raw_Actual_Input`: 4件すべて「処理済み」にチェックが入る
- `Structured_Actual_History`: 各料理が個別レコードとして作成される（例: 「キムチ鍋」「ラーメン」が別々のレコード）
- `Proposed_Dishes`: 次週7日分の献立（各日3品 = 21件程度）が作成される
- Slack: 週間献立と買い物リストが届く

#### ステップ 4: 日次リマインダーを実行

```bash
python -m src.main daily
```

このコマンドは以下を実行します:

1. **未処理の実績データを構造化** (`Raw_Actual_Input` → `Structured_Actual_History`)
   - `Raw_Actual_Input` の「処理済み」が `false` のレコードを自動処理
   - `Structured_Actual_History` に構造化データを作成
   - 元のレコードを「処理済み」に更新

2. **日次リマインダーをSlackに送信**
   - 今日の献立予定を通知
   - 実績入力用のNotionリンクを送信

→ **確認**:
- `Raw_Actual_Input` の未処理レコードが「処理済み」に更新される
- `Structured_Actual_History` にデータが追加される
- Slack に今日の献立リマインダーが届く

#### ステップ 5: 再テスト

```bash
# データをリセットして最初からやり直し
python -m src.main reset --force
python -m src.main seed
python -m src.main weekly
```

### テストケース一覧

| テストケース | コマンド | 確認ポイント |
|-------------|---------|-------------|
| 空のDBで献立生成 | `reset --force` → `weekly` | 実績なしでも献立が生成される |
| 実績ありで献立生成 | `reset --force` → `seed` → `weekly` | 実績を考慮した献立が生成される |
| 日次リマインダー | `daily` | 今日の献立がSlackに通知される |
| 日次で実績構造化 | `reset --force` → `seed` → `daily` | 未処理実績が構造化され、リマインダーが送信される |
| 特定日のリマインダー | `daily --date 2026-01-20` | 指定日の献立が通知される |
| 特定日基準で献立生成 | `weekly --date 2026-01-18` | 指定日を基準に次週献立を生成 |

### 献立の上書き仕様

本システムでは、自動実行時と手動実行時で異なる動作をします。

#### 自動実行モード （`python -m src.main weekly`）

毎週土曜日 06:00 に自動実行される場合：

1. **次週（月曜〜日曜）** の期間を対象とします
2. **既存の「提案」ステータスのデータのみを削除** して、新しい献立で上書きします
3. **「確定」「外食・予定あり」ステータスのデータは保護** され、削除されません

**削除対象:**
- ステータスが「提案」のレコード
- 対象期間（月曜〜日曜）内のみ

**保護対象:**
- ステータスが「確定」のレコード → 新規生成時も維持
- ステータスが「外食・予定あり」のレコード → 新規生成時も維持

#### 手動実行モード （`python -m src.main weekly --from-today`）

ユーザーが明示的に `--from-today` フラグを指定する場合：

1. **今日から7日間** の期間を対象とします
2. **既存データは削除せず、空いている日のみ生成** します
3. **既存のデータをそのまま保持** しながら、足りない日付の献立を追加

**生成対象:**
- ステータスが「提案」「確定」「外食・予定あり」いずれでもない日付のみ

**保護対象:**
- すべての既存データ → 削除されません

#### 使い分けの例

**シーン1: 毎週土曜日の定期実行（GitHub Actions）**
```bash
# 自動実行 → 次週の「提案」データを全削除して新規生成
python -m src.main weekly
# 結果: 月曜〜日曜の献立が完全に置き換わる
```

**シーン2: 途中で献立を追加したい場合（手動実行）**
```bash
# 手動実行 → 今日から7日間の空いている日のみ生成
python -m src.main weekly --from-today
# 結果: 既存データは残しつつ、不足している日の献立を補充
```

### 日次リマインダーでの実績構造化テスト

毎日19時の日次リマインダー実行時にも、未処理の `Raw_Actual_Input` が自動的に `Structured_Actual_History` に変換されます。

```bash
# 1. データをリセット
python -m src.main reset --force

# 2. テストデータを投入（未処理の実績入力として作成される）
python -m src.main seed

# 3. 日次リマインダーを実行
python -m src.main daily
```

→ **確認ポイント**:
- `Raw_Actual_Input`: 4件すべて「処理済み」にチェックが入る
- `Structured_Actual_History`: 各料理が個別レコードとして作成される
- Slack: 今日の献立リマインダーが届く（今日の献立がなければ「献立未登録」のメッセージ）

---

## トラブルシューティング

### 接続テストで失敗する

```bash
python -m src.main test
```

- **Notion**: トークンとデータベースIDを確認。インテグレーションがデータベースに接続されているか確認
- **OpenAI**: APIキーが有効か、課金設定が完了しているか確認
- **Slack**: Webhook URLが正しいか確認

### 献立が生成されない

- 全ての日に「確定」または「外食・予定あり」の予定が入っている可能性があります
- ログを確認してエラーメッセージを確認してください

### Slack通知が届かない

- Webhook URLが正しいか確認
- Slackアプリがチャンネルに追加されているか確認

---

## プロジェクト構成

```
weekly-dinner-menu/
├── .github/
│   └── workflows/
│       ├── weekly-menu.yml      # 週間献立生成ワークフロー
│       ├── daily-reminder.yml   # 日次リマインダーワークフロー
│       └── test-full-cycle.yml  # テスト用フルサイクルワークフロー
├── config/
│   ├── __init__.py
│   └── settings.py              # 設定ファイル（好み設定など）
├── src/
│   ├── __init__.py
│   ├── main.py                  # メインエントリーポイント
│   ├── notion_client.py         # Notion APIクライアント
│   ├── openai_client.py         # OpenAI APIクライアント
│   ├── slack_client.py          # Slack Webhookクライアント
│   ├── preprocessor.py          # 実績データ構造化
│   ├── menu_generator.py        # 献立生成ロジック
│   └── daily_reminder.py        # 日次リマインダー
├── tests/
│   └── __init__.py
├── .env.example                 # 環境変数のサンプル
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ライセンス

MIT License
