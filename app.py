import os
import json
from pathlib import Path

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

# Instagram music track ID.
# Add this in Render Environment Variables.
INSTAGRAM_TRACK_ID = os.environ.get("INSTAGRAM_TRACK_ID")

# Name is only used for logging.
TARGET_SONG_NAME = "Lofi Rain Instrumental"


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


# Google Drive folder URL
# IMPORTANT:
# Replace this with your real Google Drive folder URL.
BRAIN_FOLDER_URL = os.environ.get(
    "BRAIN_FOLDER_URL",
    "https://google.com"
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    "Automated post from my synchronized project brain database! "
    "🧠🤖 #fluentdome"
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ============================================================
# GEMINI CLIENT
# ============================================================

ai_client = None

if GEMINI_API_KEY:
    try:
        ai_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
        print("✅ Gemini client initialized.")
    except Exception as e:
        print(f"⚠️ Gemini initialization failed: {e}")
        ai_client = None


# ============================================================
# HISTORY FUNCTIONS
# ============================================================

def load_history():
    """
    Load list of previously posted images.
    """

    if not os.path.exists(TRACKING_FILE):
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
    """
    Save posted image history.
    """

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
    """
    Download the Google Drive folder into drive_sync.
    """

    print(
        "📥 Commencing recursive database download from Google Drive..."
    )

    if not BRAIN_FOLDER_URL:
        print("⚠️ BRAIN_FOLDER_URL is missing.")
        return False

    try:

        gdown.download_folder(
            url=BRAIN_FOLDER_URL,
            output=DOWNLOAD_DIR,
            quiet=True,
            remaining_ok=True
        )

        print(
            "✅ Google Drive asset sync completed."
        )

        return True

    except Exception as e:

        print(
            f"⚠️ Drive sync encountered warnings: {e}"
        )

        return False


# ============================================================
# KNOWLEDGE BASE
# ============================================================

def compile_knowledge_base():
    """
    Scan downloaded TXT and Markdown files and combine
    them into one context for Gemini.
    """

    context_data = ""

    if not os.path.exists(DOWNLOAD_DIR):
        return context_data

    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        # Ignore Instagram media directory
        if "Instagram" in root:
            continue

        for file in files:

            if not file.lower().endswith(
                (".txt", ".md")
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

                continue

    return context_data


# ============================================================
# CREATE REEL VIDEO
# ============================================================

def create_reel_video(target_images):
    """
    Create a simple slideshow/reel from three images.
    Each image remains on screen for 3 seconds.
    """

    print(
        f"🎬 Creating video from: "
        f"{[os.path.basename(x) for x in target_images]}"
    )

    clips = []

    try:

        for image_path in target_images:

            clip = (
                ImageClip(image_path)
                .with_duration(3)
            )

            clips.append(clip)

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
# GET INSTAGRAM MUSIC TRACK
# ============================================================

def get_music_track(cl):
    """
    Get Instagram music track using INSTAGRAM_TRACK_ID.

    If no track ID is configured, return None and allow
    the Reel to upload without music.
    """

    if not INSTAGRAM_TRACK_ID:

        print(
            "⚠️ INSTAGRAM_TRACK_ID is not configured."
        )

        print(
            "ℹ️ Reel will be uploaded without Instagram music."
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
            f"✅ Track loaded: {track}"
        )

        return track

    except Exception as e:

        print(
            f"⚠️ Could not load Instagram music track: {e}"
        )

        return None


# ============================================================
# POST REEL
# ============================================================

def upload_reel(cl):
    """
    Upload generated Reel.

    If INSTAGRAM_TRACK_ID exists, attempt to upload
    using Instagram music metadata.
    """

    if not os.path.exists(OUTPUT_VIDEO):

        return (
            "Error: Generated video does not exist."
        )

    track = get_music_track(cl)

    try:

        print(
            "🚀 Uploading Reel..."
        )

        # ----------------------------------------------------
        # Upload WITH Instagram music
        # ----------------------------------------------------

        if track:

            try:

                media = cl.clip_upload_with_music(
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
                    f"⚠️ Music upload failed: {music_error}"
                )

                print(
                    "🔄 Trying normal Reel upload..."
                )

        # ----------------------------------------------------
        # Fallback: normal Reel upload
        # ----------------------------------------------------

        media = cl.clip_upload(
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
# PROCESS IMAGES AND POST
# ============================================================

def process_and_post_slideshow(cl):
    """
    Select three images, create Reel, upload it,
    then save the images to posting history.
    """

    history = load_history()

    valid_exts = (
        ".jpg",
        ".jpeg",
        ".png"
    )

    # --------------------------------------------------------
    # Check Instagram folder
    # --------------------------------------------------------

    if not os.path.exists(
        INSTAGRAM_IMAGE_DIR
    ):

        return (
            "Error: Sync completed but "
            "'Instagram' media queue subfolder "
            "was not found."
        )

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Find images not posted before
    # --------------------------------------------------------

    unposted_images = [
        image
        for image in all_images
        if image not in history
    ]

    # --------------------------------------------------------
    # Reset history when all images were used
    # --------------------------------------------------------

    if len(unposted_images) < 3:

        print(
            "🔄 Not enough unposted images."
        )

        print(
            "🔄 Resetting posting history..."
        )

        history = []

        unposted_images = all_images

    # --------------------------------------------------------
    # Need at least 3 images
    # --------------------------------------------------------

    if len(unposted_images) < 3:

        return (
            "Error: At least 3 images are required "
            "to create a Reel."
        )

    # --------------------------------------------------------
    # Select first 3
    # --------------------------------------------------------

    target_images = unposted_images[:3]

    print(
        "🎯 Selected images:"
    )

    for image in target_images:
        print(
            f"   - {os.path.basename(image)}"
        )

    # --------------------------------------------------------
    # Create video
    # --------------------------------------------------------

    video_created = create_reel_video(
        target_images
    )

    if not video_created:

        return (
            "Error: Could not create Reel video."
        )

    # --------------------------------------------------------
    # Upload Reel
    # --------------------------------------------------------

    upload_result = upload_reel(
        cl
    )

    # --------------------------------------------------------
    # Only save history if upload succeeded
    # --------------------------------------------------------

    if upload_result.startswith(
        "Success:"
    ):

        for image in target_images:

            if image not in history:
                history.append(image)

        save_history(
            history
        )

        print(
            "✅ Posting history updated."
        )

    return upload_result


# ============================================================
# MONITOR AND REPLY TO COMMENTS
# ============================================================

def monitor_and_reply_to_comments(cl):
    """
    Check recent Instagram posts for comments and use
    Gemini to generate replies from the knowledge base.
    """

    if not ai_client:

        return (
            "Comment processor skipped: "
            "Gemini API key missing."
        )

    print(
        "💬 Scanning recent media timeline..."
    )

    try:

        # ----------------------------------------------------
        # Get user ID
        # ----------------------------------------------------

        user_id = cl.user_id_from_username(
            USERNAME
        )

        # ----------------------------------------------------
        # Get latest posts
        # ----------------------------------------------------

        user_medias = cl.user_medias(
            user_id,
            amount=3
        )

        # ----------------------------------------------------
        # Load knowledge
        # ----------------------------------------------------

        knowledge_context = (
            compile_knowledge_base()
        )

        if not knowledge_context:

            knowledge_context = (
                "No specific internal company notes "
                "are available. Reply politely as a "
                "helpful AI assistant."
            )

        # ----------------------------------------------------
        # Process each post
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # Process comments
            # ------------------------------------------------

            for comment in comments:

                # Ignore own comments
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

                    # ----------------------------------------
                    # Gemini prompt
                    # ----------------------------------------

                    ai_prompt = f"""
You are the AI operations representative
for the platform '{USERNAME}'.

Below is the knowledge database derived
from our project vault files:

{knowledge_context}

A user @{comment.user.username}
left this comment on our Instagram post:

"{comment.text}"

Formulate a short, natural and friendly reply.

Use exclusively the facts provided above.

Do not invent information.

Do not sound robotic.

Maximum 2 short sentences.
"""

                    # ----------------------------------------
                    # Generate reply
                    # ----------------------------------------

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

                        print(
                            "⚠️ Gemini returned empty response."
                        )

                        continue

                    # ----------------------------------------
                    # Reply to comment
                    # ----------------------------------------

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
# HOME ROUTE
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
# AUTOMATION ROUTE
# ============================================================

@app.route(
    "/run-automation",
    methods=["GET", "POST"]
)
def trigger_automation():

    # --------------------------------------------------------
    # Check environment variables
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Google Drive synchronization
    # --------------------------------------------------------

    sync_google_drive()

    # --------------------------------------------------------
    # Instagram client
    # --------------------------------------------------------

    cl = Client()

    try:

        print(
            "🔐 Logging into Instagram using session ID..."
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

    # --------------------------------------------------------
    # Post Reel
    # --------------------------------------------------------

    posting_log = (
        process_and_post_slideshow(
            cl
        )
    )

    # --------------------------------------------------------
    # Process comments
    # --------------------------------------------------------

    comment_log = (
        monitor_and_reply_to_comments(
            cl
        )
    )

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

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
