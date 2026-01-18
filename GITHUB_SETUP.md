# GitHub Actions 設定ガイド

このドキュメントでは、GitHub Actions を使用して自動的に献立生成と日次リマインダーを実行するための設定手順を説明します。

## 概要

本プロジェクトには 2 つの GitHub Actions ワークフローが含まれています：

1. **Weekly Menu Generation** (`weekly-menu.yml`)
   - **実行スケジュール**: 毎週土曜日 06:00 JST
   - **処理内容**: 次週の献立を自動生成してSlackに通知
   - **手動実行**: 可能（Actions タブから実行可能）

2. **Daily Reminder** (`daily-reminder.yml`)
   - **実行スケジュール**: 毎日 19:00 JST
   - **処理内容**: 今日の献立と実績入力のリマインドをSlackに送信
   - **手動実行**: 可能（Actions タブから実行可能）

---

## 前提条件

GitHub Actions を使用する前に、以下の準備が完了していることを確認してください：

1. ✅ Notion API トークンが取得できている
2. ✅ 3つのNotion データベースが作成済み（提案メニュー、実績入力、実績履歴）
3. ✅ OpenAI API キーが取得できている
4. ✅ Slack Webhook URL が取得できている
5. ✅ このリポジトリを GitHub にプッシュ済み

詳細は [README.md](README.md) の「環境変数の設定」セクションを参照してください。

---

## GitHub Secrets の設定

GitHub Actions で使用する環境変数は、すべて **GitHub Secrets** として登録する必要があります。

### Secrets 登録手順

1. GitHub リポジトリを開く
2. 上部メニューから **Settings** をクリック
3. 左メニューから **Secrets and variables** → **Actions** をクリック
4. **New repository secret** をクリック

### 登録するシークレット一覧

以下のシークレットを登録してください（✅ は必須、オプションは任意）：

| Secret Name | 必須 | 値 | 説明 |
|------------|:----:|------|------|
| `NOTION_TOKEN` | ✅ | `secret_xxxx...` | Notion Integration トークン |
| `DB_ID_PROPOSED` | ✅ | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | 提案メニューテーブルのID（32文字） |
| `DB_ID_RAW` | ✅ | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | 実績入力テーブルのID（32文字） |
| `DB_ID_STRUCTURED` | ✅ | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | 実績履歴テーブルのID（32文字） |
| `OPENAI_API_KEY` | ✅ | `sk-xxxx...` | OpenAI API キー |
| `SLACK_WEBHOOK_URL` | ✅ | `https://hooks.slack.com/services/...` | Slack Webhook URL |
| `USER_DIETARY_PREFERENCES` | - | （下記参照） | 食事の好み・制限（プライベート情報用） |

### 各値の取得方法

#### 1. NOTION_TOKEN
- [Notion Developers](https://www.notion.so/my-integrations) にアクセス
- 「新しいインテグレーション」から取得したトークン
- 形式: `secret_` で始まる長い文字列

#### 2. DB_ID_PROPOSED / DB_ID_RAW / DB_ID_STRUCTURED
- Notion データベースを開く
- URL から取得：
  ```
  https://www.notion.so/your-workspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                        この32文字がID
  ```
- ハイフン（-）なしの 32 文字の16進数文字列

#### 3. OPENAI_API_KEY
- [OpenAI Platform](https://platform.openai.com/api-keys) にアクセス
- API キーを生成
- 形式: `sk-` で始まる文字列

#### 4. SLACK_WEBHOOK_URL
- [Slack API](https://api.slack.com/apps) にアクセス
- アプリの「Incoming Webhooks」から取得
- 形式: `https://hooks.slack.com/services/` で始まる URL

#### 5. USER_DIETARY_PREFERENCES（オプション）

**プライバシーに関わる食事の好み・制限を設定するためのシークレットです。**

アレルギー、健康状態、家族構成など、公開リポジトリのコードに書きたくない情報を安全に管理できます。

**設定形式**：
```
- 妊婦がいるため生魚・生肉は避ける\n- 子供が食べやすい味付け\n- 辛いものは控える\n- 調理時間は30分以内
```

**注意点**：
- 改行は `\n` で表現してください
- ダブルクォートで囲む必要はありません
- 設定しない場合はデフォルトの汎用的な好みが使用されます

**設定例**：
- `- 妊婦がいるため生魚は避ける\n- 塩分控えめ`
- `- 乳製品アレルギーあり\n- グルテンフリー`
- `- 高齢者向けの柔らかい料理\n- 減塩メニュー`

---

## ワークフロー設定の詳細

### 1. 週間献立生成ワークフロー (`weekly-menu.yml`)

```yaml
# 毎週土曜日 06:00 JST に実行
schedule:
  - cron: '0 21 * * 5'  # 金曜日 21:00 UTC = 土曜日 06:00 JST
```

**特徴:**
- 自動実行時は「提案」ステータスのデータを削除して上書き
- 「確定」「外食・予定あり」ステータスは保護される
- 手動実行時にオプションで基準日を指定可能

**手動実行方法:**
1. GitHub リポジトリの **Actions** タブをクリック
2. 左メニューから **Weekly Menu Generation** を選択
3. **Run workflow** ドロップダウンから **Run workflow** をクリック
4. （オプション）**reference_date** に日付を入力（`YYYY-MM-DD` 形式）
5. **Run workflow** をクリック

### 2. 日次リマインダーワークフロー (`daily-reminder.yml`)

```yaml
# 毎日 19:00 JST に実行
schedule:
  - cron: '0 10 * * *'  # 毎日 10:00 UTC = 毎日 19:00 JST
```

**特徴:**
- 未処理の実績データを自動的に構造化
- 今日の献立をSlackに通知
- 実績入力のリマインドを送信

**手動実行方法:**
1. GitHub リポジトリの **Actions** タブをクリック
2. 左メニューから **Daily Reminder** を選択
3. **Run workflow** ドロップダウンから **Run workflow** をクリック
4. （オプション）**target_date** に日付を入力（`YYYY-MM-DD` 形式）
5. **Run workflow** をクリック

---

## 実行スケジュールのカスタマイズ

デフォルトの実行スケジュールを変更したい場合は、ワークフロー YAML ファイルの `cron` 式を編集してください。

### Cron 式の書き方

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, 0 = Sunday)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

### よくある設定例

**毎日午前 8 時に実行**
```yaml
schedule:
  - cron: '0 8 * * *'
```

**毎週月曜日午前 6 時に実行**
```yaml
schedule:
  - cron: '0 6 * * 1'
```

**毎月 1 日午前 12 時に実行**
```yaml
schedule:
  - cron: '0 0 1 * *'
```

**複数の時間帯で実行**
```yaml
schedule:
  - cron: '0 6 * * *'   # 朝 6 時
  - cron: '0 18 * * *'  # 夜 18 時
```

### UTC から JST への変換

GitHub Actions のクーロンジョブは UTC タイムゾーンで実行されます。JST（日本標準時）に変換する場合は、UTC 時刻から 9 時間引いてください。

| 希望時刻（JST） | UTC 時刻 | Cron 式 |
|---------------|---------|---------|
| 06:00 JST | 21:00 UTC (前日) | `0 21 * * 5` (金曜) |
| 19:00 JST | 10:00 UTC | `0 10 * * *` |
| 09:00 JST | 00:00 UTC | `0 0 * * *` |
| 18:00 JST | 09:00 UTC | `0 9 * * *` |

---

## 実行状況の確認

### ワークフロー実行履歴の確認

1. GitHub リポジトリの **Actions** タブをクリック
2. 確認したいワークフロー（Weekly Menu Generation または Daily Reminder）を選択
3. 実行履歴が表示されます

### 実行ログの確認

1. 実行履歴からジョブをクリック
2. 各ステップのログが表示されます
3. エラーが発生した場合は、ログにエラーメッセージが記録されます

### Slack 連携確認

- ✅ 献立が正常に生成されると、Slack に通知が届きます
- ✅ Slack に通知が届かない場合は、Webhook URL が正しいか確認してください

---

## トラブルシューティング

### ワークフロー実行が失敗する

**症状**: Actions タブで赤い ✗ が表示されている

**原因と対策**:

1. **Secrets が正しく設定されていない**
   - Settings → Secrets and variables → Actions で全ての Secret が正しく登録されているか確認
   - 値にスペースや改行がないか確認
   - Secret のキー名が正確か確認（大文字小文字を区別）

2. **Notion API エラー**
   - NOTION_TOKEN が有効か確認
   - DB_ID_PROPOSED / DB_ID_RAW / DB_ID_STRUCTURED が正しいか確認
   - インテグレーションがデータベースに接続されているか確認

3. **OpenAI API エラー**
   - OPENAI_API_KEY が有効か確認
   - OpenAI の課金設定が完了しているか確認
   - API 利用限度を超えていないか確認

4. **Slack Webhook エラー**
   - SLACK_WEBHOOK_URL が正しいか確認
   - Slack アプリがチャンネルに追加されているか確認

### Slack に通知が届かない

**確認ポイント**:
1. Webhook URL が正しいか確認
2. チャンネルに Slack App が追加されているか確認
3. ワークフローのログでエラーがないか確認

### スケジュール実行されない

GitHub Actions のスケジュール実行に関する注意:
- スケジュール実行は、**リポジトリが public** の場合のみ 動作します
- 60 日以上プッシュが無い場合、スケジュール実行が停止します
- 何かしらのプッシュを行うと、スケジュール実行が再開されます

**対策**:
- リポジトリが public になっているか確認
- 定期的にプッシュを行う（README 更新など）
- または手動実行で動作確認

---

## セキュリティに関する注意

### Secrets 管理

- ✅ 本番環境では絶対に Secrets を `.env` ファイルとしてリポジトリにコミットしないでください
- ✅ `.env` ファイルは `.gitignore` に含まれているため、自動的にコミットされません
- ✅ GitHub Secrets は暗号化されており、ログには出力されません

### トークンの更新

API トークンを定期的に更新することをお勧めします：
1. OpenAI API キーを定期的にローテーション
2. Notion Integration トークンを必要に応じて更新
3. Slack Webhook を問題がある場合は再生成

### 環境の分離

本番環境と検証環境を分離することをお勧めします：
1. 本番用の Slack チャンネルを別途作成
2. 検証用の Notion ワークスペースを別途作成
3. 検証実行時は `ENV=development` に設定

---

## 高度な設定

### 環境変数の追加

ワークフロー内で追加の環境変数が必要な場合は、ワークフロー YAML ファイルの `env` セクションに追加できます：

```yaml
env:
  TZ: Asia/Tokyo
  LOG_LEVEL: INFO
```

### Python バージョンの変更

デフォルトは Python 3.11 です。別のバージョンを使用したい場合は、ワークフロー YAML を編集してください：

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'  # バージョンを変更
```

### ジョブの並列実行

複数のジョブを並列実行したい場合は、ワークフロー YAML で `jobs` セクションに複数のジョブを定義できます：

```yaml
jobs:
  job1:
    runs-on: ubuntu-latest
    steps:
      # ...

  job2:
    runs-on: ubuntu-latest
    steps:
      # ...
```

---

## 初期セットアップ チェックリスト

GitHub Actions でのテストを開始する前に、以下をすべて確認してください：

- [ ] 1. Notion API トークンを取得した
- [ ] 2. 3 つの Notion データベースを作成した
- [ ] 3. OpenAI API キーを取得した
- [ ] 4. Slack Webhook URL を取得した
- [ ] 5. リポジトリを GitHub にプッシュした
- [ ] 6. リポジトリが **Public** に設定されている
- [ ] 7. GitHub Settings → Secrets and variables で 6 つの Secret を登録した
- [ ] 8. Secret の値が正確に登録されている（スペースや改行なし）
- [ ] 9. 手動実行でワークフローが成功することを確認した
- [ ] 10. Slack に通知が届くことを確認した
- [ ] 11. スケジュール時刻が希望時刻になっているか確認した（必要に応じて Cron 式を編集）

---

## よくある質問（FAQ）

### Q: ローカルでテストしてから GitHub Actions で実行したい

**A**: 以下の手順でテストしてください：

```bash
# 1. 仮想環境を作成
python3 -m venv venv

# 2. 仮想環境を有効化
source venv/bin/activate

# 3. 依存関係をインストール
pip install -r requirements.txt

# 4. ローカル .env ファイルで設定
cp .env.example .env
# .env を編集して値を設定

# 5. テスト実行
python -m src.main test    # 接続テスト
python -m src.main weekly  # 献立生成テスト
python -m src.main daily   # リマインダーテスト
```

### Q: 実行日時を変更したい

**A**: ワークフロー YAML ファイルの `cron` 式を編集してください：

```yaml
schedule:
  - cron: '0 6 * * 0'  # 毎週日曜日 06:00 JST に変更
```

詳細は「実行スケジュールのカスタマイズ」セクションを参照。

### Q: 複数のバージョンで同時にテストしたい

**A**: ワークフロー YAML で `strategy.matrix` を使用します：

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
```

### Q: GitHub Actions 無料枠でどのくらい実行できる？

**A**: GitHub Free プランでは以下の制限があります：
- **毎月 2,000 分** のアクション実行時間
- 本システムは 1 実行あたり 1-2 分程度のため、毎日実行しても 60-120 分/月
- 十分に無料枠内で運用可能です

---

## 次のステップ

1. ✅ 全ての Secret を登録する
2. ✅ 手動実行でワークフローをテストする
3. ✅ Slack 通知が届くことを確認する
4. ✅ スケジュール実行を待つ（または手動実行で検証）
5. ✅ ログを定期的に確認する

---

## サポート

問題が発生した場合は、以下をご確認ください：
1. [README.md](README.md) - トラブルシューティングセクション
2. GitHub Actions ログ - 詳細なエラーメッセージ
3. Slack Webhook の動作確認 - 別途テスト送信

ご質問や問題報告は、GitHub Issues に報告してください。
