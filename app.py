import os
import json
import shutil

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


# ============================================================
# GOOGLE DRIVE
# ============================================================

# Main Brain folder
BRAIN_FOLDER_URL = (
    "https://drive.google.com/drive/folders/"
    "1xdraEwHizlHyZggtbl3o2zrpybzz8wUS?usp=sharing"
)

# IMPORTANT:
# This is the Content_queue folder ID found in your
# Render logs.
CONTENT_QUEUE_FOLDER_ID = (
    "108KPkhzu-Q4hCngNXVF73ytYKmk2nI4j"
)

CONTENT_QUEUE_URL = (
    "https://drive.google.com/drive/folders/"
    f"{CONTENT_QUEUE_FOLDER_ID}"
)


# ============================================================
# INSTAGRAM MUSIC
# ============================================================

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

# Images are now downloaded directly from
# Instagram/Content_queue
INSTAGRAM_IMAGE_DIR = os.path.join(
    DOWNLOAD_DIR,
    "Instagram",
    "Content_queue"
)

KNOWLEDGE_DIR = os.path.join(
    DOWNLOAD_DIR,
    "Knowledge"
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

os.makedirs(
    KNOWLEDGE_DIR,
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
# POSTING HISTORY
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
# CLEAN OLD CONTENT QUEUE
# ============================================================

def clean_content_queue():

    if os.path.exists(
        INSTAGRAM_IMAGE_DIR
    ):

        try:

            shutil.rmtree(
                INSTAGRAM_IMAGE_DIR
            )

            print(
                "🧹 Old Content_queue removed."
            )

        except Exception as e:

            print(
                f"⚠️ Could not clean old Content_queue: {e}"
            )


# ============================================================
# GOOGLE DRIVE - KNOWLEDGE FILES
# ============================================================

# These are the small Markdown files identified in your
# Render logs.
#
# Instead of downloading the entire Brain, we download
# only these important knowledge files individually.

KNOWLEDGE_FILES = [

    {
        "id": "1TJPIOJFkZU9REr4pNBKoudyp2YmtJNnc",
        "name": "Home.md"
    },

    {
        "id": "1hMYYAko_ByOQAEJ8jySvUWLp9q-eHbhy",
        "name": "Actions, Blockers & Risks.md"
    },

    {
        "id": "1CGA8Nsb7Wtc3-Banv9j8Kjhcb89g8L7T",
        "name": "Project Facts & Decisions.md"
    },

    {
        "id": "1YBue5n4qdd8VAYq0omHyCIlda2uj3xBX",
        "name": "Product & Inventory.md"
    },

    {
        "id": "1wNOp6dLvwNcJtBHCFr7b9YwOO-gmaSg4",
        "name": "Approved Sales Facts & FAQ.md"
    },

    {
        "id": "1ZNxdCADANdqFtXAqnBXqQP47sSqbFFcr",
        "name": "Sales, Objections & Competitor Analysis.md"
    },

    {
        "id": "1HmrGDJbDtIQvtI_yIhIYh1dG06tzZJb1",
        "name": "01 Rules.md"
    },

    {
        "id": "1Hfxun8kEeZQ0XmdZpVaWnKIdsVqlVj32",
        "name": "03 Approved images.md"
    },

    {
        "id": "1oFaybXbM9X79x8i8py_wiMkrPbXhCz67",
        "name": "04 General Posts.md"
    },

    {
        "id": "1q9fLH7F8seATgnQUuvHAaEqEh6Qle4Hz",
        "name": "05 Published Posts.md"
    },

    {
        "id": "13cyQSh47QyRML4Io30sImZVH5XSyA-Dk",
        "name": "06 Templates.md"
    },

    {
        "id": "1cGa_AKfNPXNpEu8dRxzZ1N3oVAv-Ce7g",
        "name": "Source Register.md"
    }
]


# ============================================================
# DOWNLOAD ONE KNOWLEDGE FILE
# ============================================================

def download_knowledge_file(
    file_id,
    filename
):

    output_path = os.path.join(
        KNOWLEDGE_DIR,
        filename
    )

    try:

        print(
            f"📄 Downloading knowledge file: "
            f"{filename}"
        )

        result = gdown.download(
            id=file_id,
            output=output_path,
            quiet=False
        )

        if result:

            print(
                f"✅ Knowledge file downloaded: "
                f"{filename}"
            )

            return True

        print(
            f"⚠️ Could not download: {filename}"
        )

        return False

    except Exception as e:

        print(
            f"⚠️ Knowledge download failed "
            f"for {filename}: {e}"
        )

        return False


# ============================================================
# GOOGLE DRIVE SYNC
# ============================================================

def sync_google_drive():

    print(
        "\n📥 Starting Google Drive synchronization..."
    )

    print(
        f"📁 Main Brain: {BRAIN_FOLDER_URL}"
    )

    print(
        f"📸 Content queue: {CONTENT_QUEUE_URL}"
    )

    try:

        # ----------------------------------------------------
        # 1. CLEAN OLD CONTENT QUEUE
        # ----------------------------------------------------

        clean_content_queue()

        os.makedirs(
            INSTAGRAM_IMAGE_DIR,
            exist_ok=True
        )

        # ----------------------------------------------------
        # 2. DOWNLOAD ONLY CONTENT_QUEUE
        # ----------------------------------------------------

        print(
            "\n📸 Downloading Instagram Content_queue..."
        )

        downloaded_images = (
            gdown.download_folder(
                url=CONTENT_QUEUE_URL,
                output=INSTAGRAM_IMAGE_DIR,
                quiet=False,
                remaining_ok=True
            )
        )

        if not downloaded_images:

            print(
                "⚠️ Content_queue returned no files."
            )

            return False

        print(
            "\n✅ Instagram Content_queue downloaded."
        )

        # ----------------------------------------------------
        # 3. DOWNLOAD KNOWLEDGE FILES
        # ----------------------------------------------------

        print(
            "\n🧠 Downloading knowledge files..."
        )

        successful_knowledge = 0

        for item in KNOWLEDGE_FILES:

            success = download_knowledge_file(
                item["id"],
                item["name"]
            )

            if success:

                successful_knowledge += 1

        print(
            f"\n✅ Knowledge synchronization finished."
        )

        print(
            f"📚 Knowledge files downloaded: "
            f"{successful_knowledge}/"
            f"{len(KNOWLEDGE_FILES)}"
        )

        # ----------------------------------------------------
        # 4. VERIFY CONTENT QUEUE
        # ----------------------------------------------------

        if not os.path.isdir(
            INSTAGRAM_IMAGE_DIR
        ):

            print(
                "❌ Content_queue directory "
                "was not created."
            )

            return False

        valid_extensions = (
            ".jpg",
            ".jpeg",
            ".png"
        )

        image_count = 0

        for root, dirs, files in os.walk(
            INSTAGRAM_IMAGE_DIR
        ):

            for file in files:

                if file.lower().endswith(
                    valid_extensions
                ):

                    image_count += 1

        print(
            f"📸 Images available: {image_count}"
        )

        if image_count == 0:

            print(
                "❌ No images found in Content_queue."
            )

            return False

        print(
            "\n🎉 Google Drive synchronization "
            "completed successfully."
        )

        return True

    except Exception as e:

        print(
            f"\n❌ Google Drive sync failed: {e}"
        )

        return False


# ============================================================
# KNOWLEDGE BASE
# ============================================================

def compile_knowledge_base():

    context_data = ""

    if not os.path.exists(
        KNOWLEDGE_DIR
    ):

        return context_data

    for root, dirs, files in os.walk(
        KNOWLEDGE_DIR
    ):

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
                    f"\n"
                    f"--- Source File: {file} ---\n"
                    f"{content}\n"
                )

            except Exception as e:

                print(
                    f"⚠️ Could not read "
                    f"{file}: {e}"
                )

    return context_data


# ============================================================
# CREATE REEL VIDEO
# ============================================================

def create_reel_video(
    target_images
):

    print(
        "\n🎬 Creating Reel from:"
    )

    for image in target_images:

        print(
            f"   - {os.path.basename(image)}"
        )

    clips = []

    video = None

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

        print(
            "🎞️ Rendering video..."
        )

        video.write_videofile(
            OUTPUT_VIDEO,
            fps=24,
            codec="libx264",
            audio=False,
            logger=None
        )

        print(
            f"✅ Video created: "
            f"{OUTPUT_VIDEO}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Video creation failed: {e}"
        )

        return False

    finally:

        if video:

            try:

                video.close()

            except Exception:
                pass

        for clip in clips:

            try:

                clip.close()

            except Exception:
                pass


# ============================================================
# GET INSTAGRAM MUSIC
# ============================================================

def get_music_track(
    cl
):

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

def upload_reel(
    cl
):

    if not os.path.exists(
        OUTPUT_VIDEO
    ):

        return (
            "Error: Generated video "
            "does not exist."
        )

    track = get_music_track(
        cl
    )

    try:

        print(
            "\n🚀 Uploading Reel..."
        )

        # ----------------------------------------------------
        # TRY WITH MUSIC
        # ----------------------------------------------------

        if track:

            try:

                cl.clip_upload_with_music(
                    path=OUTPUT_VIDEO,
                    caption=DEFAULT_CAPTION,
                    track=track
                )

                print(
                    "🎉 SUCCESS! Reel posted "
                    "with music."
                )

                return (
                    "Success: Reel generated "
                    "and posted with Instagram music."
                )

            except Exception as music_error:

                print(
                    "⚠️ Music upload failed: "
                    f"{music_error}"
                )

                print(
                    "🔄 Trying normal Reel upload..."
                )

        # ----------------------------------------------------
        # NORMAL REEL UPLOAD
        # ----------------------------------------------------

        cl.clip_upload(
            path=OUTPUT_VIDEO,
            caption=DEFAULT_CAPTION
        )

        print(
            "🎉 SUCCESS! Reel posted "
            "without music."
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
# FIND CONTENT QUEUE IMAGES
# ============================================================

def find_content_images():

    valid_exts = (
        ".jpg",
        ".jpeg",
        ".png"
    )

    images = []

    if not os.path.isdir(
        INSTAGRAM_IMAGE_DIR
    ):

        return images

    # os.walk is used because gdown may preserve
    # nested folders.
    for root, dirs, files in os.walk(
        INSTAGRAM_IMAGE_DIR
    ):

        for filename in sorted(files):

            if filename.lower().endswith(
                valid_exts
            ):

                images.append(
                    os.path.join(
                        root,
                        filename
                    )
                )

    return sorted(
        images
    )


# ============================================================
# PROCESS IMAGES
# ============================================================

def process_and_post_slideshow(
    cl
):

    history = load_history()

    all_images = find_content_images()

    if not all_images:

        return (
            "Error: No valid images found inside "
            "Instagram/Content_queue."
        )

    print(
        f"\n📸 Found {len(all_images)} images "
        f"in Content_queue."
    )

    # --------------------------------------------------------
    # FIND UNPOSTED IMAGES
    # --------------------------------------------------------

    unposted_images = [
        image
        for image in all_images
        if image not in history
    ]

    # --------------------------------------------------------
    # RESET HISTORY WHEN NECESSARY
    # --------------------------------------------------------

    if len(unposted_images) < 3:

        print(
            "🔄 Fewer than 3 unposted images remain."
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

    # --------------------------------------------------------
    # SELECT THREE IMAGES
    # --------------------------------------------------------

    target_images = unposted_images[:3]

    print(
        "\n🎯 Selected images:"
    )

    for image in target_images:

        print(
            f"   - {os.path.basename(image)}"
        )

    # --------------------------------------------------------
    # CREATE VIDEO
    # --------------------------------------------------------

    video_created = create_reel_video(
        target_images
    )

    if not video_created:

        return (
            "Error: Could not create Reel video."
        )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    upload_result = upload_reel(
        cl
    )

    # --------------------------------------------------------
    # SAVE HISTORY ONLY AFTER SUCCESS
    # --------------------------------------------------------

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
# MONITOR AND REPLY TO COMMENTS
# ============================================================

def monitor_and_reply_to_comments(
    cl
):

    if not ai_client:

        return (
            "Comment processor skipped: "
            "Gemini API key missing."
        )

    print(
        "\n💬 Scanning recent media timeline..."
    )

    try:

        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

        user_id = cl.user_id_from_username(
            USERNAME
        )

        # ----------------------------------------------------
        # GET RECENT MEDIA
        # ----------------------------------------------------

        user_medias = cl.user_medias(
            user_id,
            amount=3
        )

        # ----------------------------------------------------
        # LOAD KNOWLEDGE
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

        print(
            f"🧠 Knowledge base characters: "
            f"{len(knowledge_context)}"
        )

        # ----------------------------------------------------
        # PROCESS MEDIA
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
            # PROCESS COMMENTS
            # ------------------------------------------------

            for comment in comments:

                # Don't reply to yourself
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
                    # GEMINI PROMPT
                    # ----------------------------------------

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

                    # ----------------------------------------
                    # GEMINI REQUEST
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
                        if response.text
                        else ""
                    )

                    if not reply_text:

                        print(
                            "⚠️ Gemini returned "
                            "an empty response."
                        )

                        continue

                    # ----------------------------------------
                    # POST REPLY
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

        print(
            f"⚠️ Comment processor warning: {e}"
        )

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

    print(
        "\n=================================================="
    )

    print(
        "🏁 AUTONOMOUS ROUTINE INITIATED"
    )

    print(
        "=================================================="
    )

    # ========================================================
    # CHECK ENVIRONMENT VARIABLES
    # ========================================================

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

    # ========================================================
    # GOOGLE DRIVE
    # ========================================================

    drive_synced = sync_google_drive()

    if not drive_synced:

        print(
            "❌ Automation stopped because "
            "Google Drive synchronization failed."
        )

        return jsonify(
            {
                "status": "Failed",

                "error":
                    "Google Drive synchronization failed."
            }
        ), 500

    # ========================================================
    # INSTAGRAM LOGIN
    # ========================================================

    cl = Client()

    try:

        print(
            "\n🔐 Logging into Instagram "
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

        print(
            f"❌ Instagram authentication failed: {e}"
        )

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

    print(
        "\n🎬 Starting Reel creation/posting..."
    )

    posting_log = (
        process_and_post_slideshow(
            cl
        )
    )

    # ========================================================
    # COMMENTS
    # ========================================================

    print(
        "\n💬 Starting comment processing..."
    )

    comment_log = (
        monitor_and_reply_to_comments(
            cl
        )
    )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    print(
        "\n=================================================="
    )

    print(
        "🏁 AUTONOMOUS ROUTINE FINISHED"
    )

    print(
        "=================================================="
    )

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
