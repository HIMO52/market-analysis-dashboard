# market-analysis-dashboard

株式・ETF・ニュースを自動収集し、相関分析やトレンドをまとめて表示するダッシュボードです。

**重要:** これは投資助言システムではありません。「買い」「売り」の判断は行わず、
データ・相関・トレンドを一箇所にまとめて見えるようにすることが目的です。
実際の証券口座への発注機能・自動売買機能・実際のお金を扱う機能は一切含みません。

## 全体の仕組み

```
GitHub Actions（定期実行・無料枠内）
  ↓ 株価・ニュースを取得
  ↓ 分析（相関・リターン・移動平均など）を計算
  ↓ Web表示用のJSONを生成
GitHub Pages（静的サイト）
  ↓
iPhoneのSafariなどブラウザから閲覧
```

PCは最初の開発時だけ使い、完成後は起動しっぱなしにする必要はありません。
更新はすべてGitHub Actionsのクラウド上で行われます。

## 開発の進め方（フェーズ）

| Phase | 内容 | 状態 |
|---|---|---|
| 1 | プロジェクト基盤 | ✅ 完了 |
| 2 | 市場データ取得 | ✅ 完了 |
| 3 | データ保存（SQLite） | ✅ 完了 |
| 4 | テクニカル分析 | ✅ 完了 |
| 5 | 相関分析 | ✅ 完了 |
| 6 | 逆相関ペア分析 | ✅ 完了 |
| 7 | ニュース収集 | ✅ 完了 |
| 8〜9 | ニュース関連付け・重要度 | ✅ 完了 |
| 10〜11 | 市場イベント・値動き分析 | ✅ 完了 |
| 12〜13 | GitHub Actions定期実行 | 未着手 |
| 14 | Webダッシュボード / GitHub Pages | 未着手 |

## フォルダ構成

```
config/           設定ファイル（銘柄リスト、閾値など）。コードを触らず変更可能
  tickers.yaml      監視銘柄リスト
  settings.yaml     相関の閾値、DBパスなどの全体設定
src/              Pythonソースコード
  config.py         設定ファイルの読み込み共通処理
  data_sources/     株価データ取得（Phase 2で実装、交換可能な構造にする）
  analysis/         テクニカル分析・相関計算（Phase 4〜6）
  news/             ニュース収集・分類（Phase 7〜9）
  webdata/          Web表示用JSON生成（Phase 14）
tests/            自動テスト
data/
  db/               SQLiteデータベース（Gitには含めない）
  raw/              一時的な生データ置き場
scripts/          手動実行用の補助スクリプト
.github/workflows/  GitHub Actionsの定期実行設定（Phase 13）
docs/             GitHub Pagesで公開する静的サイト（Phase 14）
.env.example      環境変数のサンプル（実際の.envはGitに含めない）
```

## セットアップ（自分のPCで動作確認する場合）

```bash
# 1. 仮想環境を作る
python3 -m venv venv
source venv/bin/activate   # Windowsは venv\Scripts\activate

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. 環境変数ファイルを用意（今のところ必須の値はありません）
cp .env.example .env

# 4. テストを実行
pytest tests/ -v
```

## APIキー・秘密情報の扱い方（GitHub Secretsの設定手順）

このプロジェクトは現時点（Phase 1〜2）では必須のAPIキーを使いません。
将来ニュースAPIなどで鍵が必要になった場合は、以下の手順でGitHub Secretsに登録します。

1. GitHubでこのリポジトリのページを開く
2. 上部メニューの `Settings` をクリック
3. 左メニューの `Secrets and variables` → `Actions` をクリック
4. `New repository secret` をクリック
5. `Name` に鍵の名前（例: `NEWSAPI_KEY`）、`Secret` に実際の値を入力して `Add secret`

**注意:** `.env` ファイルやAPIキーの実際の値をこのREADMEやコードに直接書かないでください。
`.gitignore` により `.env` は自動的にGitの管理対象から除外されます。

## 無料枠・レート制限について（分かり次第ここに追記していきます）

- GitHub Actions: パブリックリポジトリは無料枠が大きいですが無制限ではありません
- yfinance: 無料ですが取得頻度が高すぎると一時的にブロックされることがあります
- ニュースRSS(CNBC / MarketWatch / WSJ): 無料の公開フィードですが、各社の利用規約は変わることがあるため、定期的に確認してください。過度に高頻度でアクセスしないようにしています
- 各データ取得元の詳細な制限は、実装が進むごとにこのセクションに追記します
