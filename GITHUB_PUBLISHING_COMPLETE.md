# GitHub リポジトリ公開完了

プロジェクト「Dinner-Aide」の GitHub への公開が完了しました！

## 公開リポジトリ情報

- **リポジトリ名**: weekly-dinner-menu
- **リポジトリ URL**: https://github.com/taikik5/weekly-dinner-menu
- **アクセス**: Public（パブリック）
- **ライセンス**: MIT License

---

## 公開内容

✅ **次のファイルが公開されています**:
- Python ソースコード（src/ フォルダ）
- 設定ファイル（config/ フォルダ）
- テストファイル（tests/ フォルダ）
- ドキュメント（README.md, ARCHITECTURE.md など）
- GitHub Actions ワークフロー（.github/workflows/）
- 設定テンプレート（.env.example）
- その他必要なファイル（requirements.txt, .gitignore など）

✅ **機密情報は完全に除外されています**:
- ❌ .env ファイル（実際のシークレット）は未公開
- ✅ .env.example（プレースホルダー）は公開
- ✅ .gitignore により自動的に保護
- ✅ GitHub の Push Protection により検証済み

---

## GitHub Actions 自動実行の設定

GitHub Actions で自動実行するには、**6 つの GitHub Secrets** を登録する必要があります。

### セットアップ手順（所要時間: 5 分）

#### ステップ 1: GitHub リポジトリの Settings を開く

1. https://github.com/taikik5/weekly-dinner-menu にアクセス
2. 上部メニューから **Settings** をクリック
3. 左メニューから **Secrets and variables** → **Actions** をクリック

#### ステップ 2: 6 つの Secrets を登録

**New repository secret** をクリックして、以下をそれぞれ登録してください：

```
Secret Name: NOTION_TOKEN
Value: secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
（Notion Developers から取得したトークン）

Secret Name: DB_ID_PROPOSED
Value: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
（提案メニューテーブルの ID、32 文字）

Secret Name: DB_ID_RAW
Value: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
（実績入力テーブルの ID、32 文字）

Secret Name: DB_ID_STRUCTURED
Value: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
（実績履歴テーブルの ID、32 文字）

Secret Name: OPENAI_API_KEY
Value: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
（OpenAI API キー）

Secret Name: SLACK_WEBHOOK_URL
Value: https://hooks.slack.com/services/...
（Slack Webhook URL）
```

#### ステップ 3: 登録内容を確認

Settings → Secrets and variables → Actions で、以下の 6 つが表示されていることを確認：
- ✅ NOTION_TOKEN
- ✅ DB_ID_PROPOSED
- ✅ DB_ID_RAW
- ✅ DB_ID_STRUCTURED
- ✅ OPENAI_API_KEY
- ✅ SLACK_WEBHOOK_URL

---

## ワークフロー実行スケジュール

登録後、以下のスケジュールで **自動的に** 実行されます：

### 1. 週間献立生成
- **実行日時**: 毎週 **土曜日 06:00 JST**
- **処理内容**: 次週の献立を自動生成してSlackに通知
- **ワークフロー**: `.github/workflows/weekly-menu.yml`
- **変更可能**: ✅ 実行時刻を Cron 式で変更可能

### 2. 日次リマインダー
- **実行日時**: 毎日 **19:00 JST**
- **処理内容**: 今日の献立をSlackに通知し、実績入力をリマインド
- **ワークフロー**: `.github/workflows/daily-reminder.yml`
- **変更可能**: ✅ 実行時刻を Cron 式で変更可能

---

## GitHub Actions での初期テスト（推奨）

Secret を登録した後、以下の手順で動作確認をしてください：

### テスト実行方法

1. GitHub リポジトリの **Actions** タブをクリック
2. 左メニューから **Weekly Menu Generation** を選択
3. **Run workflow** ボタンをクリック
4. **Run workflow** をクリック

### 期待される動作

✅ ワークフローが実行される（数秒〜1 分程度）
✅ Slack に献立通知が送信される
✅ Actions ログに「Generating menu for ...」と表示される

もし赤い ✗ が表示された場合は、「トラブルシューティング」を参照してください。

---

## スケジュール実行時刻のカスタマイズ

デフォルトの実行時刻を変更したい場合は、ワークフロー YAML ファイルを編集してください。

### ファイル編集方法

1. GitHub リポジトリを開く
2. `.github/workflows/weekly-menu.yml` または `daily-reminder.yml` をクリック
3. 右上の ✏️ アイコンをクリック（Edit this file）
4. `cron:` の値を変更
5. **Commit changes** をクリック

### Cron 式の書き方

```yaml
# 毎週土曜日 06:00 JST (= 金曜日 21:00 UTC)
- cron: '0 21 * * 5'

# 毎日 19:00 JST (= 10:00 UTC)
- cron: '0 10 * * *'

# 毎日 09:00 JST (= 00:00 UTC)
- cron: '0 0 * * *'

# 毎週月曜日 08:00 JST (= 日曜日 23:00 UTC)
- cron: '0 23 * * 0'
```

**重要**: GitHub Actions は UTC タイムゾーンで実行されるため、JST に変換する場合は 9 時間を引いてください。

詳細は [GITHUB_SETUP.md](GITHUB_SETUP.md) を参照してください。

---

## トラブルシューティング

### ❌ ワークフロー実行が失敗する

**確認項目**:

1. **Secrets が正しく登録されているか？**
   ```
   Settings → Secrets and variables → Actions
   → 6 つすべてが表示されているか確認
   → 値にスペースや改行がないか確認
   ```

2. **Notion API の確認**
   ```
   - トークンが有効か？
   - データベースIDが正確か？（ハイフンなし 32 文字）
   - インテグレーションがデータベースに接続されているか？
   ```

3. **OpenAI API の確認**
   ```
   - API キーが有効か？
   - 課金設定が完了しているか？
   - 利用限度に達していないか？
   ```

4. **Slack Webhook の確認**
   ```
   - URL が正しいか？
   - Slack App がチャンネルに追加されているか？
   ```

### ❌ Slack に通知が届かない

**確認項目**:
1. Webhook URL が正しいか確認
2. チャンネルに App が追加されているか確認
3. GitHub Actions ログでエラーがないか確認

### ❌ スケジュール実行されない

GitHub Actions の制限事項:
- リポジトリが **Public** である必要があります ✅（確認済み）
- 60 日以上プッシュがない場合、スケジュール実行が停止します
- 対策: 定期的にプッシュを行うか、手動実行でテスト

---

## 本番環境への推奨事項

本番環境での安定運用のため、以下をお勧めします：

### セキュリティ

- [ ] 定期的に API トークンをローテーション
- [ ] Secrets は GitHub のみで管理（ローカルファイルに含めない）
- [ ] 機密情報が含まれたコミットは絶対にしない

### 監視

- [ ] 定期的に GitHub Actions のログを確認
- [ ] Slack 通知で異常を早期発見
- [ ] エラーが発生したら即座に確認・対応

### バックアップ

- [ ] Notion データベースを定期的にエクスポート
- [ ] 重要な献立データは別途保管

---

## ドキュメント

本プロジェクトには以下のドキュメントが含まれています：

1. **README.md** - プロジェクト概要、セットアップガイド、使い方
2. **GITHUB_SETUP.md** - GitHub Actions の詳細な設定ガイド（このファイル）
3. **ARCHITECTURE.md** - プロジェクトアーキテクチャ、設計思想
4. **TESTING.md** - テスト方法、テストケース

---

## よくある質問

### Q: ローカルでも実行できる?

**A**: はい、可能です。
```bash
python -m src.main test    # 接続テスト
python -m src.main weekly  # 献立生成
python -m src.main daily   # リマインダー
```
詳細は README.md を参照してください。

### Q: 献立生成の好みをカスタマイズできる?

**A**: はい、できます。
`config/settings.py` の `USER_DIETARY_PREFERENCES` を編集してください。

### Q: データベースをリセットしたい

**A**: ローカルでは `python -m src.main reset --force` で可能です。
GitHub Actions では Secret を削除して再登録するか、新しいデータベースを使用してください。

### Q: 複数の Slack チャンネルに送信したい

**A**: 複数の Webhook URL を設定し、`src/slack_client.py` を編集して複数回送信するように変更できます。

---

## 次のステップ

1. ✅ Secret を 6 つ登録する
2. ✅ 手動実行でワークフローをテストする
3. ✅ Slack に通知が届くことを確認する
4. ✅ スケジュール時刻が正しいか確認する（必要に応じて Cron 式を編集）
5. ✅ 定期的にログを確認して正常に動作していることを確認する

---

## サポート

問題が発生した場合：

1. 📖 このドキュメントのトラブルシューティングセクションを確認
2. 📖 [GITHUB_SETUP.md](GITHUB_SETUP.md) で詳細な設定方法を確認
3. 📖 [README.md](README.md) で全般的な使い方を確認
4. 🐛 GitHub Issues で問題を報告

---

## リポジトリリンク

🔗 **https://github.com/taikik5/weekly-dinner-menu**

このリポジトリをスターしていただけると、開発の励みになります！⭐

---

**公開日**: 2026-01-18
**ステータス**: ✅ 公開完了、すべてのセットアップが完了したら GitHub Actions で自動実行が開始されます
