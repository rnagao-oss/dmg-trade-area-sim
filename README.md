# DMG商圏シミュレーション

## ローカル起動
```bash
cd gis_app
pip install -r requirements.txt
streamlit run app.py
```
→ http://localhost:8501 で開く

## Streamlit Cloud (無料) でデプロイ
1. GitHubアカウントを用意（無料）
2. このフォルダ全体（`gis_app/`）を新規GitHubリポジトリにpush
3. https://streamlit.io/cloud → "New app"
4. GitHubリポジトリを連携、`app.py` を指定
5. デプロイすると `https://xxxx.streamlit.app` のURLが発行される
6. このURLを先方に共有 → 誰でもブラウザで操作可能

## 機能
- 中心点プリセット（池袋・新宿・渋谷・東京等）/ カスタム住所入力
- 半径マルチ選択（3/5/7/10/12/15/20/25/30km）
- 獲得率スライダー（0-50%）
- 戸数フィルター（デフォルト60-100戸）
- 半径別物件数/総戸数/獲得想定の即時集計
- マップ上の物件プロット＋ポップアップ
- 圏内物件リストCSVダウンロード

## データ
- 全742物件をジオコード済 → `data/properties.json`
- 出典：吉川氏提供「②加工_2024~2025_竣工物件リスト」
