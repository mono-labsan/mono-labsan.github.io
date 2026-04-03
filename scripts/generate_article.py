"""
毎日自動で記事を3本生成し content/posts/ に保存するスクリプト。
GitHub Actions から実行される。
"""

import os
import re
import sys
import json
import time
import random
from datetime import datetime
from pathlib import Path

from groq import Groq

# --- 設定 ---
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]
AMAZON_TAG     = os.environ.get("AMAZON_ASSOCIATE_TAG", "xxxxxxxx-22")
ARTICLES_PER_RUN = 1
USED_FILE = Path("scripts/used_keywords.json")

client = Groq(api_key=GROQ_API_KEY)

# --- キーワード戦略 ---
PRODUCTS = [
    "ワイヤレスイヤホン", "有線イヤホン", "ノイズキャンセリングイヤホン",
    "メカニカルキーボード", "ゲーミングキーボード", "テンキーレスキーボード",
    "ゲーミングマウス", "トラックボールマウス", "静音マウス",
    "モバイルバッテリー", "急速充電モバイルバッテリー",
    "USB-Cハブ", "ドッキングステーション", "HDMIセレクター",
    "Webカメラ", "4K Webカメラ", "テレワーク用Webカメラ",
    "外付けSSD", "ポータブルHDD", "NAS",
    "ノートPCスタンド", "モニターアーム", "PCデスク",
    "ワイヤレス充電器", "MagSafe充電器", "充電スタンド",
    "スマートウォッチ", "スマートバンド", "GPSウォッチ",
    "ゲーミングヘッドセット", "ワイヤレスヘッドセット",
    "液晶モニター", "4Kモニター", "ゲーミングモニター", "湾曲モニター",
    "ポータブルスピーカー", "Bluetoothスピーカー", "防水スピーカー",
    "ドライブレコーダー", "前後カメラドライブレコーダー",
    "ロボット掃除機", "コードレス掃除機",
    "電動歯ブラシ", "口腔洗浄器",
    "スマートホームデバイス", "スマートスピーカー",
    "プロジェクター", "小型プロジェクター",
    "Kindle", "電子書籍リーダー",
    "ゲーミングチェア", "オフィスチェア",
]

TEMPLATES = [
    "{product} おすすめ ランキング TOP5【2025年最新】",
    "{product} 比較【2025年版】選び方と人気モデルを徹底解説",
    "コスパ最強 {product} おすすめ 厳選5選",
    "{product} 選び方 失敗しないポイントと人気商品",
    "1万円以下 {product} おすすめ 2025年版",
    "テレワーク向け {product} おすすめランキング",
    "{product} 初心者向け おすすめ 完全ガイド",
    "{product} 人気モデル徹底比較【専門家が解説】",
]

def load_used():
    if USED_FILE.exists():
        return set(json.loads(USED_FILE.read_text(encoding="utf-8")))
    return set()

def save_used(used: set):
    USED_FILE.write_text(
        json.dumps(sorted(used), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def pick_keyword(used: set):
    candidates = []
    for product in PRODUCTS:
        for tpl in TEMPLATES:
            kw = tpl.format(product=product)
            if kw not in used:
                candidates.append((kw, product))
    if not candidates:
        print("⚠ 全キーワード使用済み。リセットします。")
        save_used(set())
        return pick_keyword(set())
    return random.choice(candidates)

def amazon_search_url(product: str) -> str:
    import urllib.parse
    q = urllib.parse.quote(product)
    return f"https://www.amazon.co.jp/s?k={q}&tag={AMAZON_TAG}"

def generate_content(keyword: str, product: str) -> str | None:
    prompt = f"""
あなたはガジェット比較サイトの専門ライターです。
以下のキーワードで日本語のSEO記事を書いてください。

キーワード: {keyword}
ターゲット商品カテゴリ: {product}

# 記事の要件
- 文字数: 2500〜3500字
- 読者: ガジェット初心者〜中級者
- H2見出し5個程度、H3を適宜使用
- 最新のウェブ情報を検索して、実際に販売されている商品を5つ紹介する
- 各商品に: 商品名、価格帯、主なスペック、メリット・デメリット、こんな人におすすめ
- 各商品紹介の直後に必ず以下の形式のAmazonリンクを入れる:
  [Amazonで価格を確認する]({amazon_search_url(product)})
- 記事末尾に「まとめ・結論」セクション（どれを買うべきか明確に）
- 自然で読みやすい日本語。押しつけがましくなく、中立的なトーン

# 禁止事項
- 架空の商品名・スペックを書かない
- 誇大広告・根拠のない最上級表現（「業界No.1」等）を使わない
- 個人の健康・金融・法律に関わる断言

# 出力形式
Hugo Markdownの本文のみ。front matterは含めないこと。
見出しは ## と ### を使用。
"""
    for attempt in range(3):
        try:
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4096,
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            print(f"  エラー全文: {e}")
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 30 * (2 ** attempt)
                print(f"  レート制限。{wait}秒待機...")
                time.sleep(wait)
            else:
                return None
    return None

def build_frontmatter(keyword: str, product: str) -> str:
    now = datetime.now()
    # front matter 用に " をエスケープ
    safe_kw = keyword.replace('"', '\\"')
    desc = f"{keyword}を徹底比較。おすすめモデルをランキング形式で紹介します。"
    return f"""---
title: "{safe_kw}"
date: {now.strftime('%Y-%m-%dT%H:%M:%S+09:00')}
draft: false
description: "{desc}"
categories: ["{product}"]
tags: ["{product}", "比較", "おすすめ", "ランキング", "2025"]
---

{{{{< rawhtml >}}}}
<div style="background:#fff8dc;border-left:4px solid #f0ad4e;padding:10px 14px;margin-bottom:24px;font-size:0.9em;">
<strong>【広告・アフィリエイト開示】</strong>本記事にはAmazonアソシエイトのリンクが含まれます。リンク経由での購入時に手数料を受け取る場合がありますが、紹介内容の公平性に一切影響しません。
</div>
{{{{< /rawhtml >}}}}

"""

def slug_from_keyword(keyword: str) -> str:
    # 日本語をローマ字化せずそのまま使うと URL が長くなるので英語ハッシュを使う
    import hashlib
    h = hashlib.md5(keyword.encode()).hexdigest()[:8]
    safe = re.sub(r'[^\w]', '-', keyword)[:30]
    return f"{safe}-{h}"

def save_article(keyword: str, product: str, body: str) -> Path:
    now = datetime.now()
    slug = slug_from_keyword(keyword)
    filename = f"{now.strftime('%Y-%m-%d')}-{slug}.md"

    posts_dir = Path("content/posts")
    posts_dir.mkdir(parents=True, exist_ok=True)

    filepath = posts_dir / filename
    filepath.write_text(
        build_frontmatter(keyword, product) + body,
        encoding="utf-8"
    )
    return filepath

def main():
    used = load_used()
    print(f"使用済みキーワード: {len(used)}件")

    newly_used = set()
    success = 0

    for i in range(ARTICLES_PER_RUN):
        keyword, product = pick_keyword(used | newly_used)
        print(f"\n[{i+1}/{ARTICLES_PER_RUN}] 生成中: {keyword}")

        body = generate_content(keyword, product)
        if not body:
            print(f"  ⚠ 生成失敗。スキップ。")
            continue

        path = save_article(keyword, product, body)
        newly_used.add(keyword)
        success += 1
        print(f"  ✅ 保存: {path}")

        if i < ARTICLES_PER_RUN - 1:
            time.sleep(8)  # APIレート制限対策

    save_used(used | newly_used)
    print(f"\n完了: {success}/{ARTICLES_PER_RUN}本 生成")
    if success == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
