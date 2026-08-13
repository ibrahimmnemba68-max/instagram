import os
import json

import gdown
from flask import Flask, jsonify
from instagrapi import Client
from moviepy import ImageClip, concatenate_videoclips
from google import genai


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = "fluentdome"

# Your Google Drive brain folder
BRAIN_FOLDER_URL = (
    "https://drive.google.com/drive/folders/"
    "1xdraEwHizlHyZggtbl3o2zrpybzz8wUS?usp=sharing"
)

# Instagram music track ID
INSTAGRAM_TRACK_ID = os.environ.get(
    "INSTAGRAM_TRACK_ID"
)

TARGET_SONG_NAME = "Lofi Rain Instrumental"


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

SESSION_ID = os.environ.get(
    "INSTAGRAM_SESSION_ID"
)

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY"
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "drive_sync"
)

INSTAGRAM_IMAGE_DIR = os.path.join(
    DOWNLOAD_DIR,
    "Instagram"
)

OUTPUT_VIDEO = os.path.join(
    BASE_DIR,
    "generated_reel.mp4"
)

TRACKING_FILE = os.path.join(
    BASE_DIR,
    "posted_history.json"
)


# ============================================================
# DEFAULT CAPTION
# ============================================================

DEFAULT_CAPTION = (
    "Automated post from my synchronized "
    "project brain database! "
    "🧠🤖 #fluentdome"
)


# ============================================================
# CREATE DIRECTORIES
# ============================================================

os.makedirs(
    DOWNLOAD_DIR,
    exist_ok=True
)


# ============================================================
# GEMINI CLIENT
# ============================================================

ai_client = None

if GEMINI_API_KEY:
    try:

        ai_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print(
            "✅ Gemini client initialized."
        )

    except Exception as e:

        print(
            f"⚠️ Gemini initialization failed: {e}"
        )

        ai_client = None


# ============================================================
# HISTORY
# ============================================================

def load_history():

    if not os.path.exists(
        TRACKING_FILE
    ):
        return []

    try:

        with open(
            TRACKING_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"⚠️ Could not load history file: {e}"
        )

        return []


def save_history(history):

    try:

        with open(
            TRACKING_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                history,
                f,
                indent=4
            )

    except Exception as e:

        print(
            f"⚠️ Could not save history: {e}"
        )


# ============================================================
# GOOGLE DRIVE SYNC
# ============================================================

def sync_google_drive():

    print(
        "📥 Commencing recursive database "
        "download from Google Drive..."
    )

    print(
        f"📁 Drive folder: {BRAIN_FOLDER_URL}"
    )

    try:

        # Make sure old download directory exists
        os.makedirs(
            DOWNLOAD_DIR,
            exist_ok=True
        )

        downloaded = gdown.download_folder(
            url=BRAIN_FOLDER_URL,
            output=DOWNLOAD_DIR,
            quiet=False,
            remaining_ok=True
        )

        # gdown may return None/empty when nothing was downloaded
        if not downloaded:

            print(
                "⚠️ Google Drive returned no downloaded files."
            )

            return False

        print(
            "✅ Google Drive asset sync completed."
        )

        # Check for Instagram folder
        if not os.path.isdir(
            INSTAGRAM_IMAGE_DIR
        ):

            print(
                "❌ Instagram folder was not found."
            )

            print(
                f"Expected folder: {INSTAGRAM_IMAGE_DIR}"
            )

            return False

        print(
            f"✅ Instagram folder found: "
            f"{INSTAGRAM_IMAGE_DIR}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Drive sync failed: {e}"
        )

        return False


# ============================================================
# KNOWLEDGE BASE
# ============================================================

def compile_knowledge_base():

    context_data = ""

    if not os.path.exists(
        DOWNLOAD_DIR
    ):
        return context_data

    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        # Don't read Instagram images as knowledge
        if os.path.abspath(
            root
        ).startswith(
            os.path.abspath(
                INSTAGRAM_IMAGE_DIR
            )
        ):
            continue

        for file in files:

            if not file.lower().endswith(
                (
                    ".txt",
                    ".md"
                )
            ):
                continue

            file_path = os.path.join(
                root,
                file
            )

            try:

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    content = f.read()

                context_data += (
                    f"\n--- Source File: {file} ---\n"
                    f"{content}\n"
                )

            except Exception as e:

                print(
                    f"⚠️ Could not read {file}: {e}"
                )

    return context_data


# ============================================================
# CREATE REEL
# ============================================================

def create_reel_video(target_images):

    print(
        "🎬 Creating video from:"
    )

    for image in target_images:

        print(
            f"   - {os.path.basename(image)}"
        )

    clips = []

    try:

        for image_path in target_images:

            clip = (
                ImageClip(
                    image_path
                )
                .with_duration(3)
            )

            clips.append(
                clip
            )

        video = concatenate_videoclips(
            clips,
            method="compose"
        )

        video.write_videofile(
            OUTPUT_VIDEO,
            fps=24,
            codec="libx264",
            audio=False,
            logger=None
        )

        video.close()

        for clip in clips:

            clip.close()

        print(
            f"✅ Video created: {OUTPUT_VIDEO}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Video creation failed: {e}"
        )

        return False


# ============================================================
# GET INSTAGRAM MUSIC
# ============================================================

def get_music_track(cl):

    if not INSTAGRAM_TRACK_ID:

        print(
            "⚠️ INSTAGRAM_TRACK_ID is not configured."
        )

        print(
            "ℹ️ Reel will be uploaded without music."
        )

        return None

    try:

        print(
            f"🎵 Fetching Instagram track: "
            f"{TARGET_SONG_NAME}"
        )

        track = cl.track_info_by_id(
            INSTAGRAM_TRACK_ID
        )

        print(
            "✅ Instagram music track loaded."
        )

        return track

    except Exception as e:

        print(
            f"⚠️ Could not load Instagram music: {e}"
        )

        return None


# ============================================================
# UPLOAD REEL
# ============================================================

def upload_reel(cl):

    if not os.path.exists(
        OUTPUT_VIDEO
    ):

        return (
            "Error: Generated video does not exist."
        )

    track = get_music_track(
        cl
    )

    try:

        print(
            "🚀 Uploading Reel..."
        )

        # Try music first
        if track:

            try:

                cl.clip_upload_with_music(
                    path=OUTPUT_VIDEO,
                    caption=DEFAULT_CAPTION,
                    track=track
                )

                print(
                    "🎉 SUCCESS! Reel posted with music."
                )

                return (
                    "Success: Reel generated and "
                    "posted with Instagram music."
                )

            except Exception as music_error:

                print(
                    f"⚠️ Music upload failed: "
                    f"{music_error}"
                )

                print(
                    "🔄 Trying normal Reel upload..."
                )

        # Normal Reel upload
        cl.clip_upload(
            path=OUTPUT_VIDEO,
            caption=DEFAULT_CAPTION
        )

        print(
            "🎉 SUCCESS! Reel posted without music."
        )

        return (
            "Success: Reel generated and "
            "posted without Instagram music."
        )

    except Exception as e:

        print(
            f"❌ Reel upload failed: {e}"
        )

        return (
            f"Error: Reel upload failed: {e}"
        )


# ============================================================
# PROCESS IMAGES
# ============================================================

def process_and_post_slideshow(cl):

    history = load_history()

    valid_exts = (
        ".jpg",
        ".jpeg",
        ".png"
    )

    # Check Instagram folder
    if not os.path.isdir(
        INSTAGRAM_IMAGE_DIR
    ):

        return (
            "Error: Instagram folder was not found."
        )

    # Find images
    all_images = [
        os.path.join(
            INSTAGRAM_IMAGE_DIR,
            filename
        )

        for filename in sorted(
            os.listdir(
                INSTAGRAM_IMAGE_DIR
            )
        )

        if filename.lower().endswith(
            valid_exts
        )
    ]

    if not all_images:

        return (
            "Error: No valid images found inside "
            "your Instagram cloud folder."
        )

    print(
        f"📸 Found {len(all_images)} images."
    )

    # Images not posted before
    unposted_images = [
        image
        for image in all_images
        if image not in history
    ]

    # Reset when fewer than 3 remain
    if len(unposted_images) < 3:

        print(
            "🔄 Not enough unposted images."
        )

        print(
            "🔄 Resetting posting history..."
        )

        history = []

        unposted_images = all_images

    if len(unposted_images) < 3:

        return (
            "Error: At least 3 images are required "
            "to create a Reel."
        )

    # Select first 3
    target_images = unposted_images[:3]

    print(
        "🎯 Selected images:"
    )

    for image in target_images:

        print(
            f"   - {os.path.basename(image)}"
        )

    # Create video
    video_created = create_reel_video(
        target_images
    )

    if not video_created:

        return (
            "Error: Could not create Reel video."
        )

    # Upload
    upload_result = upload_reel(
        cl
    )

    # Save history only after success
    if upload_result.startswith(
        "Success:"
    ):

        for image in target_images:

            if image not in history:

                history.append(
                    image
                )

        save_history(
            history
        )

        print(
            "✅ Posting history updated."
        )

    return upload_result


# ============================================================
# MONITOR COMMENTS
# ============================================================

def monitor_and_reply_to_comments(cl):

    if not ai_client:

        return (
            "Comment processor skipped: "
            "Gemini API key missing."
        )

    print(
        "💬 Scanning recent media timeline..."
    )

    try:

        user_id = cl.user_id_from_username(
            USERNAME
        )

        user_medias = cl.user_medias(
            user_id,
            amount=3
        )

        knowledge_context = (
            compile_knowledge_base()
        )

        if not knowledge_context:

            knowledge_context = (
                "No specific internal company notes "
                "are available. Reply politely as a "
                "helpful AI assistant."
            )

        for media in user_medias:

            try:

                comments = cl.media_comments(
                    media.id,
                    amount=10
                )

            except Exception as e:

                print(
                    f"⚠️ Could not read comments "
                    f"for {media.id}: {e}"
                )

                continue

            for comment in comments:

                if (
                    comment.user.username
                    == USERNAME
                ):
                    continue

                try:

                    print(
                        f"💬 Comment from "
                        f"@{comment.user.username}: "
                        f"{comment.text}"
                    )

                    ai_prompt = f"""
You are the AI operations representative
for the platform '{USERNAME}'.

Below is the knowledge database:

{knowledge_context}

A user @{comment.user.username}
left this comment:

"{comment.text}"

Formulate a short, natural and friendly reply.

Use exclusively the facts provided above.

Do not invent information.

Do not sound robotic.

Maximum 2 short sentences.
"""

                    response = (
                        ai_client
                        .models
                        .generate_content(
                            model="gemini-2.5-flash",
                            contents=ai_prompt
                        )
                    )

                    reply_text = (
                        response.text.strip()
                    )

                    if not reply_text:

                        continue

                    cl.comment_create(
                        media.id,
                        reply_text,
                        replied_to_comment_id=comment.id
                    )

                    print(
                        f"🚀 Replied to "
                        f"@{comment.user.username}: "
                        f"{reply_text}"
                    )

                except Exception as comment_error:

                    print(
                        f"⚠️ Comment processing error: "
                        f"{comment_error}"
                    )

                    continue

        return (
            "Comment checks processed completely."
        )

    except Exception as e:

        return (
            f"Comment processor warning: {e}"
        )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify(
        {
            "system":
                "Autonomous Obsidian-to-Instagram "
                "Bridge Engine Active",

            "status":
                "online"
        }
    )


# ============================================================
# AUTOMATION
# ============================================================

@app.route(
    "/run-automation",
    methods=["GET", "POST"]
)
def trigger_automation():

    # Check required environment variables
    missing_variables = []

    if not SESSION_ID:

        missing_variables.append(
            "INSTAGRAM_SESSION_ID"
        )

    if not GEMINI_API_KEY:

        missing_variables.append(
            "GEMINI_API_KEY"
        )

    if missing_variables:

        return jsonify(
            {
                "status": "Failed",

                "error":
                    "Missing Render environment "
                    "variables.",

                "missing":
                    missing_variables
            }
        ), 500

    print(
        "\n🏁 Autonomous routine initiated..."
    )

    # ========================================================
    # GOOGLE DRIVE
    # ========================================================

    drive_synced = sync_google_drive()

    if not drive_synced:

        return jsonify(
            {
                "status": "Failed",

                "error":
                    "Google Drive synchronization failed. "
                    "Check that the Google Drive folder is "
                    "shared as 'Anyone with the link' and "
                    "contains an 'Instagram' folder."
            }
        ), 500

    # ========================================================
    # INSTAGRAM
    # ========================================================

    cl = Client()

    try:

        print(
            "🔐 Logging into Instagram "
            "using session ID..."
        )

        cl.login_by_sessionid(
            SESSION_ID
        )

        cl.user_id_from_username(
            USERNAME
        )

        print(
            "✅ Instagram authentication successful."
        )

    except Exception as e:

        return jsonify(
            {
                "status": "Failed",

                "error":
                    f"Instagram Authentication Blocked: {e}"
            }
        ), 500

    # ========================================================
    # POST REEL
    # ========================================================

    posting_log = (
        process_and_post_slideshow(
            cl
        )
    )

    # ========================================================
    # COMMENTS
    # ========================================================

    comment_log = (
        monitor_and_reply_to_comments(
            cl
        )
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify(
        {
            "status": "Complete",

            "posting_result":
                posting_log,

            "comment_reply_result":
                comment_log
        }
    )


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
