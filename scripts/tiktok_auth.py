"""
TikTok OAuth認証ヘルパー
初回のみローカルで実行して refresh_token を取得する。

使い方:
  1. developers.tiktok.com でアプリを作成し CLIENT_KEY / CLIENT_SECRET を取得
  2. 以下を実行:
       python scripts/tiktok_auth.py
  3. 表示されたURLをブラウザで開いてログイン・許可
  4. リダイレクト後のURL全体をコピーして貼り付ける
  5. 表示された access_token / refresh_token を GitHub Secrets に登録
"""

import os
import sys
import urllib.parse
import requests

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY") or input("CLIENT_KEY を入力: ").strip()
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET") or input("CLIENT_SECRET を入力: ").strip()

REDIRECT_URI = "https://www.tiktok.com/auth/redirect/"   # TikTok開発者アプリで設定したURIに合わせる
SCOPE = "user.info.basic,video.publish,video.upload"

# ── Step 1: 認証URLを生成 ──────────────────────────────
params = {
    "client_key": CLIENT_KEY,
    "scope": SCOPE,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "state": "hoshi_tiktok_auth",
}
auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)

print("\n" + "="*60)
print("以下のURLをブラウザで開いてTikTokにログイン・許可してください:")
print("="*60)
print(auth_url)
print("="*60)
print("\nリダイレクト後のURL全体を貼り付けてください:")

redirected = input("> ").strip()
parsed = urllib.parse.urlparse(redirected)
code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]

if not code:
    print("❌ codeが見つかりません。URLを確認してください。")
    sys.exit(1)

print(f"\n✅ code取得: {code[:20]}...")

# ── Step 2: code → access_token / refresh_token ───────
res = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    },
    timeout=30,
)
res.raise_for_status()
data = res.json()

if "access_token" not in data:
    print(f"❌ エラー: {data}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ 認証成功！以下をGitHub Secretsに登録してください:")
print("="*60)
print(f"TIKTOK_CLIENT_KEY     = {CLIENT_KEY}")
print(f"TIKTOK_CLIENT_SECRET  = {CLIENT_SECRET}")
print(f"TIKTOK_REFRESH_TOKEN  = {data['refresh_token']}")
print("="*60)
print(f"\n（参考）access_token の有効期限: {data.get('expires_in', '?')} 秒")
print(f"（参考）refresh_token の有効期限: {data.get('refresh_expires_in', '?')} 秒")
