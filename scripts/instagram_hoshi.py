"""
ほし (Hoshi) - 星の妖精キャラクターの動画を毎日自動生成してInstagram・TikTokに投稿するスクリプト。
GitHub Actions から実行される。

必要なGitHub Secrets:
  FAL_KEY                  - fal.ai APIキー
  CLOUDINARY_CLOUD_NAME    - Cloudinaryクラウド名
  CLOUDINARY_API_KEY       - Cloudinary APIキー
  CLOUDINARY_API_SECRET    - Cloudinary APIシークレット
  INSTAGRAM_ACCESS_TOKEN   - Instagram Graph APIのアクセストークン（長期）
  INSTAGRAM_ACCOUNT_ID     - InstagramビジネスアカウントのユーザーID
  TIKTOK_CLIENT_KEY        - TikTok開発者アプリのClient Key
  TIKTOK_CLIENT_SECRET     - TikTok開発者アプリのClient Secret
  TIKTOK_REFRESH_TOKEN     - TikTok OAuthリフレッシュトークン（tiktok_auth.pyで取得）
"""

import os
import sys
import time
import random
import subprocess
import tempfile
import requests
from datetime import datetime
from pathlib import Path

import fal_client
import cloudinary
import cloudinary.uploader

# ---------------------------------------------------------------------------
# キャラクター設定
# ---------------------------------------------------------------------------

HOSHI_PROMPT = (
    "chibi fairy girl named Hoshi, "
    "tiny glowing star-shaped ahoge hair ornament, "
    "large sparkling deep violet eyes with tiny star reflections inside, "
    "pearl-white semi-translucent skin with soft golden shimmer, "
    "tiny translucent iridescent gossamer fairy wings, "
    "white romper with small gold star embroidery, "
    "round oversized chibi head, soft chubby cheeks, tiny bare feet, "
    "floating gently, "
    "kawaii anime style, pastel soft lighting, clean simple background, "
    "best quality, masterpiece, highres, 8k"
)

HOSHI_NEGATIVE = (
    "ugly, deformed, extra limbs, blurry, low quality, "
    "nsfw, adult content, realistic, 3d, dark, scary, "
    "multiple characters, text, watermark"
)

# ---------------------------------------------------------------------------
# 日替わりシチュエーション
# ---------------------------------------------------------------------------

DAILY_SCENES = [
    ("eating a giant strawberry bigger than her head, juice dripping on her cheek",
     "ほし、はじめてのいちご🍓\n#ほし #星の妖精 #chibi #kawaii #anime #cute #fairy"),
    ("curled up sleeping inside a giant open flower blossom, petals around her",
     "ほし、おはな、きもちいい〜💐💤\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("chasing a tiny glowing firefly with arms outstretched, eyes wide",
     "ほし、ほたるだ！✨🫧\n#ほし #星の妖精 #chibi #kawaii #anime #cute #fairy"),
    ("holding a teacup bigger than herself with both hands, sipping carefully",
     "ほし、おちゃ、あつい〜☕💫\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("butterfly landing on her nose, going cross-eyed in surprise",
     "ほし、ちょうちょ！びっくり！🦋✨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("blowing dandelion seeds with puffed-up cheeks, seeds floating away",
     "ほし、ふー！🌼💨\n#ほし #星の妖精 #chibi #kawaii #anime #cute #fairy"),
    ("sitting on a crescent moon with legs dangling, looking at stars",
     "ほし、おつきさまにのった！🌙⭐\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("trying to lift a single raindrop like a heavy ball, straining",
     "ほし、あめつぶ、おもたい！🌧️💪\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("floating inside a soap bubble, pressing tiny hands on the inside",
     "ほし、しゃぼんだまのなか〜🫧✨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("hugging a giant marshmallow tightly, cheeks squished",
     "ほし、ましゅまろ、やわやわ〜🤍💕\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("riding on the back of a sleepy fluffy white cat, gripping the fur",
     "ほし、ねこさんにのった！🐱🌟\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("catching falling snowflakes on her tiny tongue, eyes closed happily",
     "ほし、ゆき！あまい？❄️✨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("wrapped in a giant autumn leaf like a blanket, peeking out",
     "ほし、おちばのおふとん🍂🌟\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("looking into a tiny round mirror, surprised by her own reflection",
     "ほし、だれ！？あ、ほし！🪞💫\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("opening a tiny treasure chest, a small star shooting out",
     "ほし、たからばこ！なかにほし！⭐✨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("dancing in a shower of cherry blossom petals, arms spinning",
     "ほし、さくらの雨！🌸💃\n#ほし #星の妖精 #chibi #kawaii #anime #cute #fairy"),
    ("startled awake by a ladybug crawling on her face, arms flailing",
     "ほし、てんとうむし！びっくりした！🐞💦\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("peering curiously into a tiny mushroom house, nose almost touching door",
     "ほし、きのこのおうち、だれいる？🍄🔍\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("getting tangled in a ball of rainbow-colored yarn, flailing",
     "ほし、もつれた！🌈🧶\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("eating a giant rice ball with both hands, eyes sparkling",
     "ほし、おにぎり、おいしい！🍙⭐\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("blowing on a tiny hot bowl of ramen, cheeks puffed",
     "ほし、あつい！ふー！🍜💨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("trying to pick up a coin much bigger than herself",
     "ほし、おかね！おもたい〜💰💦\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("lying on her back looking up at stars, pointing excitedly",
     "ほし、ほしがたくさん！あれもほし！⭐🌌\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("splashing in a tiny puddle with bare feet, water droplets flying",
     "ほし、みずたまり！ぱしゃぱしゃ！💧✨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("sneaking a bite of a giant cookie while looking around suspiciously",
     "ほし、ないしょで...🍪🤫\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("spinning around trying to catch her own wings",
     "ほし、はね！はね！どこ！？🌀✨\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("falling asleep while studying a tiny open book, head drooping",
     "ほし、べんきょうちゅうに...💤📖\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("being surprised by a frog jumping out of the grass",
     "ほし、かえる！ぴょん！😱🐸\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("watering a tiny sprout with a droplet of water, watching eagerly",
     "ほし、おみず、どうぞ！🌱💧\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
    ("carrying a stack of tiny gift boxes taller than herself, wobbling",
     "ほし、たおれないで〜！🎁💫\n#ほし #星の妖精 #chibi #kawaii #anime #cute"),
]

# ---------------------------------------------------------------------------
# ステップ1: 画像生成（fal.ai Flux）
# ---------------------------------------------------------------------------

def generate_hoshi_image(scene_prompt: str) -> bytes:
    full_prompt = f"{HOSHI_PROMPT}, {scene_prompt}, vertical 9:16 composition"
    print(f"  プロンプト: {full_prompt[:80]}...")

    result = fal_client.subscribe(
        "fal-ai/flux/schnell",
        arguments={
            "prompt": full_prompt,
            "image_size": {"width": 576, "height": 1024},
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        },
    )
    image_url = result["images"][0]["url"]
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# ステップ2: 画像→動画アニメーション（fal.ai Stable Video Diffusion）
# ---------------------------------------------------------------------------

def animate_hoshi(image_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image_bytes)
        tmp_img_path = f.name

    print("  画像をfal.aiにアップロード中...")
    image_url = fal_client.upload_file(tmp_img_path)

    print("  アニメーション生成中（Stable Video Diffusion）...")
    result = fal_client.subscribe(
        "fal-ai/stable-video-diffusion",
        arguments={
            "image_url": image_url,
            "motion_bucket_id": 127,   # 高め = よく動く（最大255）
            "noise_aug_strength": 0.02,
            "fps": 7,
            "cond_aug": 0.02,
        },
    )
    video_url = result["video"]["url"]
    resp = requests.get(video_url, timeout=120)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# ステップ3: FFmpegで動画を整形（ループ・リサイズ・コーデック変換）
# ---------------------------------------------------------------------------

def process_video(video_bytes: bytes, loops: int = 5) -> bytes:
    """
    - 9:16にクロップ/パディング
    - H.264に変換
    - N回ループして長さを確保（最低3秒必要）
    - 100MB以下に収める
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.mp4"
        loop_list = Path(tmpdir) / "loop.txt"
        output_path = Path(tmpdir) / "output.mp4"

        input_path.write_bytes(video_bytes)

        # ループ用リストファイル
        with open(loop_list, "w") as f:
            for _ in range(loops):
                f.write(f"file '{input_path}'\n")

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(loop_list),
            "-vf", "scale=576:1024:force_original_aspect_ratio=decrease,"
                   "pad=576:1024:(ow-iw)/2:(oh-ih)/2:color=black",
            "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
            "-pix_fmt", "yuv420p",
            "-r", "24",
            "-movflags", "+faststart",
            "-an",                 # 音声なし（Instagram側で音楽追加推奨）
            str(output_path),
        ], check=True, capture_output=True)

        return output_path.read_bytes()


# ---------------------------------------------------------------------------
# ステップ4: Cloudinaryにアップロード（公開URL取得）
# ---------------------------------------------------------------------------

def upload_to_cloudinary(video_bytes: bytes) -> str:
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
    )

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        tmp_path = f.name

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = cloudinary.uploader.upload(
        tmp_path,
        resource_type="video",
        folder="hoshi",
        public_id=f"hoshi_{timestamp}",
        overwrite=True,
    )
    return result["secure_url"]


# ---------------------------------------------------------------------------
# ステップ5: Instagram Reelsに投稿
# ---------------------------------------------------------------------------


def post_to_instagram_reels(video_url: str, caption: str) -> str:
    account_id = os.environ["INSTAGRAM_ACCOUNT_ID"]
    access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    base = "https://graph.facebook.com/v19.0"

    # メディアコンテナ作成
    print("  Instagramメディアコンテナ作成中...")
    res = requests.post(
        f"{base}/{account_id}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": access_token,
        },
        timeout=30,
    )
    res.raise_for_status()
    container_id = res.json()["id"]
    print(f"  コンテナID: {container_id}")

    # 処理完了待機（最大5分）
    print("  処理完了を待機中...")
    for attempt in range(30):
        time.sleep(10)
        status_res = requests.get(
            f"{base}/{container_id}",
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=30,
        )
        data = status_res.json()
        status = data.get("status_code", "")
        print(f"  ステータス ({attempt+1}/30): {status}")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            raise RuntimeError(f"Instagram処理エラー: {data}")
    else:
        raise TimeoutError("Instagram動画処理がタイムアウト")

    # 公開
    print("  投稿を公開中...")
    pub_res = requests.post(
        f"{base}/{account_id}/media_publish",
        params={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    pub_res.raise_for_status()
    post_id = pub_res.json()["id"]
    return post_id



# ---------------------------------------------------------------------------
# ステップ6: TikTokに投稿
# ---------------------------------------------------------------------------

def refresh_tiktok_token() -> str:
    """リフレッシュトークンを使ってアクセストークンを自動更新"""
    res = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
        },
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    if "access_token" not in data:
        raise RuntimeError(f"TikTokトークン更新失敗: {data}")
    return data["access_token"]


def post_to_tiktok(video_url: str, caption: str) -> str:
    print("  TikTokアクセストークンを更新中...")
    access_token = refresh_tiktok_token()

    # タイトルは1行目・150文字以内
    title = caption.split("\n")[0][:150]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    payload = {
        "post_info": {
            "title": title,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
        "post_mode": "DIRECT_POST",
        "media_type": "VIDEO",
    }

    res = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json=payload,
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()

    err = data.get("error", {})
    if err.get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok投稿エラー: {data}")

    return data["data"]["publish_id"]


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    # 使用済みシーンを追跡（同じシーンが連続しないように）
    used_file = Path("scripts/hoshi_used_scenes.json")
    import json
    if used_file.exists():
        used = set(json.loads(used_file.read_text(encoding="utf-8")))
    else:
        used = set()

    available = [(i, s) for i, s in enumerate(DAILY_SCENES) if i not in used]
    if not available:
        print("全シーン使用済み。リセット。")
        used = set()
        available = list(enumerate(DAILY_SCENES))

    idx, (scene_prompt, caption) = random.choice(available)

    print(f"\n🌟 本日のほし: {caption.split(chr(10))[0]}")
    print(f"   シーン: {scene_prompt[:60]}...")

    print("\n[1/5] 画像生成中...")
    image_bytes = generate_hoshi_image(scene_prompt)
    print(f"  ✅ 画像生成完了 ({len(image_bytes)//1024}KB)")

    print("\n[2/5] アニメーション生成中...")
    video_bytes = animate_hoshi(image_bytes)
    print(f"  ✅ 動画生成完了 ({len(video_bytes)//1024}KB)")

    print("\n[3/5] 動画処理中（FFmpeg）...")
    processed = process_video(video_bytes, loops=5)
    print(f"  ✅ 動画処理完了 ({len(processed)//1024}KB)")

    print("\n[4/5] Cloudinaryにアップロード中...")
    video_url = upload_to_cloudinary(processed)
    print(f"  ✅ アップロード完了: {video_url}")

    results = []

    # Instagram
    if os.environ.get("INSTAGRAM_ACCESS_TOKEN"):
        print("\n[5/6] Instagramに投稿中...")
        try:
            ig_id = post_to_instagram_reels(video_url, caption)
            print(f"  ✅ Instagram投稿完了! 投稿ID: {ig_id}")
            results.append(f"Instagram: {ig_id}")
        except Exception as e:
            print(f"  ⚠️ Instagram投稿失敗（スキップ）: {e}")
    else:
        print("\n[5/6] INSTAGRAM_ACCESS_TOKEN未設定 → スキップ")

    # TikTok
    if os.environ.get("TIKTOK_CLIENT_KEY"):
        print("\n[6/6] TikTokに投稿中...")
        try:
            tt_id = post_to_tiktok(video_url, caption)
            print(f"  ✅ TikTok投稿完了! publish_id: {tt_id}")
            results.append(f"TikTok: {tt_id}")
        except Exception as e:
            print(f"  ⚠️ TikTok投稿失敗（スキップ）: {e}")
    else:
        print("\n[6/6] TIKTOK_CLIENT_KEY未設定 → スキップ")

    # 使用済みに追加
    used.add(idx)
    used_file.write_text(json.dumps(sorted(used), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n🎉 完了！「{caption.split(chr(10))[0]}」を投稿しました")
    for r in results:
        print(f"   {r}")


if __name__ == "__main__":
    main()
