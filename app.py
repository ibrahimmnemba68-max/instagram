import os
import json
import threading
import traceback
from datetime import datetime

import gdown
from flask import Flask, jsonify
from instagrapi import Client
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
# GOOGLE DRIVE BRAIN
# ============================================================

BRAIN_FOLDER_URL = (
    "https://drive.google.com/drive/folders/"
    "1xdraEwHizlHyZggtbl3o2zrpybzz8wUS?usp=sharing"
)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "drive_sync"
)

INSTAGRAM_IMAGE_DIR = None

TRACKING_FILE = os.path.join(
    BASE_DIR,
    "posted_history.json"
)


# ============================================================
# AUTOMATION STATE
# ============================================================

automation_lock = threading.Lock()

automation_running = False

automation_status = {
    "status": "idle",
    "message": "Automation has not been started.",
    "started_at": None,
    "finished_at": None,
    "posting_result": None,
    "comment_reply_result": None,
    "error": None
}


# ============================================================
# DEFAULT CAPTION
# ============================================================

DEFAULT_CAPTION = (
    "Discover the vision behind V Town. "
    "Where art, nature, movement and the ocean "
    "come together. 🌴🌊✨ "
    "#VTown #Zanzibar #Fumba #LuxuryLiving"
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

        print("✅ Gemini client initialized.")

    except Exception as e:

        print(
            f"⚠️ Gemini initialization failed: {e}"
        )

        ai_client = None

else:

    print(
        "⚠️ GEMINI_API_KEY is not configured."
    )


# ============================================================
# HISTORY
# ============================================================

def load_history():

    if not os.path.exists(TRACKING_FILE):

        return []

    try:

        with open(
            TRACKING_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):

            return data

        return []

    except Exception as e:

        print(
            f"⚠️ Could not load history: {e}"
        )

        return []


# ============================================================

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
                indent=4,
                ensure_ascii=False
            )

        print("✅ Posting history saved.")

    except Exception as e:

        print(
            f"⚠️ Could not save history: {e}"
        )


# ============================================================
# FIND INSTAGRAM CONTENT QUEUE
# ============================================================

def find_content_queue():

    print()
    print(
        "🔎 Searching for Instagram/Content_queue..."
    )

    if not os.path.isdir(DOWNLOAD_DIR):

        print(
            "❌ Download directory does not exist."
        )

        return None

    possible_matches = []

    for root, dirs, files in os.walk(DOWNLOAD_DIR):

        normalized_root = os.path.normpath(root)

        parts = normalized_root.split(os.sep)

        if len(parts) >= 2:

            parent_name = parts[-2].lower()
            current_name = parts[-1].lower()

            if (
                parent_name == "instagram"
                and current_name == "content_queue"
            ):

                possible_matches.append(root)

    if not possible_matches:

        print(
            "❌ Instagram/Content_queue was not found."
        )

        print()
        print(
            "📂 Downloaded directory structure:"
        )

        for root, dirs, files in os.walk(DOWNLOAD_DIR):

            level = root.replace(
                DOWNLOAD_DIR,
                ""
            ).count(os.sep)

            indent = "   " * level

            print(
                f"{indent}📁 "
                f"{os.path.basename(root) or root}"
            )

        return None

    selected = possible_matches[0]

    print(
        "✅ Instagram/Content_queue found:"
    )

    print(selected)

    if len(possible_matches) > 1:

        print()
        print(
            "⚠️ Multiple Content_queue folders found:"
        )

        for match in possible_matches:

            print(
                f"   - {match}"
            )

        print()
        print(
            "Using the first matching folder."
        )

    return selected


# ============================================================
# GOOGLE DRIVE SYNC
# ============================================================

def sync_google_drive():

    global INSTAGRAM_IMAGE_DIR

    print()
    print(
        "================================================"
    )

    print(
        "📥 STARTING GOOGLE DRIVE SYNCHRONIZATION"
    )

    print(
        "================================================"
    )

    print()
    print("📁 Drive folder:")
    print(BRAIN_FOLDER_URL)

    try:

        os.makedirs(
            DOWNLOAD_DIR,
            exist_ok=True
        )

        print()
        print(
            "⬇️ Downloading Google Drive folder..."
        )

        gdown.download_folder(
            url=BRAIN_FOLDER_URL,
            output=DOWNLOAD_DIR,
            quiet=False,
            remaining_ok=True
        )

        print()
        print(
            "📦 Google Drive download process finished."
        )

        INSTAGRAM_IMAGE_DIR = (
            find_content_queue()
        )

        if not INSTAGRAM_IMAGE_DIR:

            print()
            print(
                "❌ Could not locate Instagram/Content_queue."
            )

            return False

        image_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        )

        images = []

        for filename in os.listdir(
            INSTAGRAM_IMAGE_DIR
        ):

            if filename.lower().endswith(
                image_extensions
            ):

                full_path = os.path.join(
                    INSTAGRAM_IMAGE_DIR,
                    filename
                )

                if os.path.isfile(full_path):

                    images.append(full_path)

        images.sort(
            key=lambda x: os.path.basename(x).lower()
        )

        print()
        print(
            f"📸 Content_queue contains "
            f"{len(images)} images."
        )

        for image in images:

            print(
                f"   🖼️ "
                f"{os.path.basename(image)}"
            )

        if not images:

            print()
            print(
                "❌ No images found."
            )

            return False

        print()
        print(
            "✅ Google Drive synchronization successful."
        )

        print()
        print(
            "📂 Using image directory:"
        )

        print(INSTAGRAM_IMAGE_DIR)

        return True

    except Exception as e:

        print()
        print(
            "❌ Google Drive synchronization failed:"
        )

        print(str(e))

        traceback.print_exc()

        return False


# ============================================================
# KNOWLEDGE BASE
# ============================================================

def compile_knowledge_base():

    context_data = ""

    if not os.path.exists(DOWNLOAD_DIR):

        return context_data

    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        # ----------------------------------------------------
        # Skip Instagram image folder
        # ----------------------------------------------------

        if INSTAGRAM_IMAGE_DIR:

            try:

                image_folder = os.path.abspath(
                    INSTAGRAM_IMAGE_DIR
                )

                current_folder = os.path.abspath(
                    root
                )

                if current_folder.startswith(
                    image_folder
                ):

                    continue

            except Exception:

                pass

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
                    "\n"
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
# POST IMAGE TO INSTAGRAM
# ============================================================

def upload_image(
    cl,
    image_path
):

    if not os.path.exists(image_path):

        return (
            "Error: Image file does not exist."
        )

    try:

        print()
        print(
            "📸 Uploading image to Instagram..."
        )

        print(
            f"   {image_path}"
        )

        cl.photo_upload(
            path=image_path,
            caption=DEFAULT_CAPTION
        )

        print()
        print(
            "🎉 SUCCESS! Image posted to Instagram."
        )

        return (
            "Success: Image posted to Instagram."
        )

    except Exception as e:

        print()
        print(
            f"❌ Image upload failed: {e}"
        )

        traceback.print_exc()

        return (
            f"Error: Image upload failed: {e}"
        )


# ============================================================
# PROCESS AND POST NEXT IMAGE
# ============================================================

def process_and_post_image(cl):

    history = load_history()

    valid_exts = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    )

    if not INSTAGRAM_IMAGE_DIR:

        return (
            "Error: Instagram Content_queue "
            "was not found."
        )

    if not os.path.isdir(
        INSTAGRAM_IMAGE_DIR
    ):

        return (
            "Error: Instagram Content_queue "
            "directory does not exist."
        )

    print()
    print(
        "📂 Reading images from:"
    )

    print(INSTAGRAM_IMAGE_DIR)

    all_images = []

    for filename in sorted(
        os.listdir(
            INSTAGRAM_IMAGE_DIR
        )
    ):

        if filename.lower().endswith(
            valid_exts
        ):

            full_path = os.path.join(
                INSTAGRAM_IMAGE_DIR,
                filename
            )

            if os.path.isfile(full_path):

                all_images.append(full_path)

    print()
    print(
        f"📸 Found {len(all_images)} images."
    )

    if not all_images:

        return (
            "Error: No valid images found "
            "inside Instagram/Content_queue."
        )

    # --------------------------------------------------------
    # Remove previously posted images
    # --------------------------------------------------------

    unposted_images = [
        image
        for image in all_images
        if image not in history
    ]

    print()
    print(
        f"📊 Previously posted: "
        f"{len(all_images) - len(unposted_images)}"
    )

    print(
        f"📊 Remaining: "
        f"{len(unposted_images)}"
    )

    # --------------------------------------------------------
    # Reset when all images have been posted
    # --------------------------------------------------------

    if not unposted_images:

        print()
        print(
            "🔄 All images have already been posted."
        )

        print(
            "🔄 Resetting posting history."
        )

        history = []

        unposted_images = all_images

    if not unposted_images:

        return (
            "Error: No images available."
        )

    # --------------------------------------------------------
    # Select ONE image
    # --------------------------------------------------------

    target_image = unposted_images[0]

    print()
    print(
        "🎯 Selected image:"
    )

    print(
        f"   {os.path.basename(target_image)}"
    )

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    upload_result = upload_image(
        cl,
        target_image
    )

    # --------------------------------------------------------
    # Save history ONLY after successful upload
    # --------------------------------------------------------

    if upload_result.startswith(
        "Success:"
    ):

        if target_image not in history:

            history.append(
                target_image
            )

        save_history(history)

        print()
        print(
            "✅ Image posting history updated."
        )

    return upload_result


# ============================================================
# MONITOR COMMENTS AND REPLY USING GEMINI
# ============================================================

def monitor_and_reply_to_comments(cl):

    if not ai_client:

        return (
            "Comment processor skipped: "
            "Gemini API key missing."
        )

    print()
    print(
        "💬 Scanning recent Instagram posts..."
    )

    try:

        # ----------------------------------------------------
        # Get account ID
        # ----------------------------------------------------

        user_id = cl.user_id_from_username(
            USERNAME
        )

        # ----------------------------------------------------
        # Get recent posts
        # ----------------------------------------------------

        user_medias = cl.user_medias(
            user_id,
            amount=3
        )

        # ----------------------------------------------------
        # Build knowledge base
        # ----------------------------------------------------

        knowledge_context = (
            compile_knowledge_base()
        )

        if not knowledge_context:

            knowledge_context = (
                "No specific internal company "
                "notes are available. "
                "Reply politely as a helpful "
                "assistant without inventing facts."
            )

        # ----------------------------------------------------
        # Process recent posts
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

                try:

                    # ----------------------------------------
                    # Ignore own comments
                    # ----------------------------------------

                    if (
                        comment.user.username.lower()
                        == USERNAME.lower()
                    ):

                        continue

                    print()
                    print(
                        f"💬 Comment from "
                        f"@{comment.user.username}:"
                    )

                    print(
                        comment.text
                    )

                    # ----------------------------------------
                    # Gemini prompt
                    # ----------------------------------------

                    ai_prompt = f"""
You are the AI customer-support representative
for "{USERNAME}".

You are replying to a comment on Instagram.

Below is the internal company knowledge:

{knowledge_context}

Instagram user:
@{comment.user.username}

Their comment:
"{comment.text}"

Write a short, natural and friendly reply.

Rules:

1. Use ONLY facts contained in the knowledge above.
2. Do NOT invent prices, dates, locations, features,
   availability, promises or other information.
3. If the knowledge does not contain the answer,
   politely tell the user that the team can provide
   more details.
4. Be helpful and conversational.
5. Do not sound robotic.
6. Maximum 2 short sentences.
7. Do not use hashtags unless they are necessary.
"""

                    # ----------------------------------------
                    # Generate Gemini response
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

                    print()
                    print(
                        f"🚀 Replied to "
                        f"@{comment.user.username}:"
                    )

                    print(
                        reply_text
                    )

                except Exception as comment_error:

                    print()
                    print(
                        "⚠️ Comment processing error:"
                    )

                    print(
                        str(comment_error)
                    )

                    continue

        return (
            "Comment checks processed completely."
        )

    except Exception as e:

        print()
        print(
            f"⚠️ Comment processor warning: {e}"
        )

        traceback.print_exc()

        return (
            f"Comment processor warning: {e}"
        )


# ============================================================
# ACTUAL AUTOMATION
# ============================================================

def run_automation_background():

    global automation_running
    global automation_status

    try:

        automation_status.update(
            {
                "status": "running",
                "message":
                    "Automation is running.",
                "started_at":
                    datetime.utcnow().isoformat(),
                "finished_at":
                    None,
                "posting_result":
                    None,
                "comment_reply_result":
                    None,
                "error":
                    None
            }
        )

        print()
        print(
            "============================================"
        )

        print(
            "🏁 AUTONOMOUS ROUTINE STARTED"
        )

        print(
            "============================================"
        )

        # ====================================================
        # GOOGLE DRIVE
        # ====================================================

        drive_synced = (
            sync_google_drive()
        )

        if not drive_synced:

            raise RuntimeError(
                "Google Drive synchronization failed."
            )

        # ====================================================
        # INSTAGRAM SESSION
        # ====================================================

        if not SESSION_ID:

            raise RuntimeError(
                "INSTAGRAM_SESSION_ID is missing."
            )

        cl = Client()

        print()
        print(
            "🔐 Logging into Instagram..."
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

        # ====================================================
        # POST IMAGE
        # ====================================================

        posting_log = (
            process_and_post_image(
                cl
            )
        )

        automation_status[
            "posting_result"
        ] = posting_log

        # ====================================================
        # COMMENTS
        # ====================================================

        comment_log = (
            monitor_and_reply_to_comments(
                cl
            )
        )

        automation_status[
            "comment_reply_result"
        ] = comment_log

        # ====================================================
        # COMPLETE
        # ====================================================

        automation_status.update(
            {
                "status":
                    "completed",

                "message":
                    "Automation completed successfully.",

                "finished_at":
                    datetime.utcnow().isoformat()
            }
        )

        print()
        print(
            "============================================"
        )

        print(
            "🎉 AUTOMATION COMPLETED"
        )

        print(
            "============================================"
        )

    except Exception as e:

        print()
        print(
            "❌ AUTOMATION FAILED"
        )

        print(
            str(e)
        )

        traceback.print_exc()

        automation_status.update(
            {
                "status":
                    "failed",

                "message":
                    "Automation failed.",

                "finished_at":
                    datetime.utcnow().isoformat(),

                "error":
                    str(e)
            }
        )

    finally:

        automation_running = False

        try:

            automation_lock.release()

        except RuntimeError:

            pass


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify(
        {
            "system":
                "Autonomous Obsidian-to-Instagram "
                "Image Bridge Engine",

            "status":
                "online",

            "features":
                {
                    "google_drive_sync":
                        True,

                    "image_posting":
                        True,

                    "gemini_comments":
                        True,

                    "video_generation":
                        False,

                    "reels":
                        False,

                    "instagram_music":
                        False
                },

            "automation":
                automation_status
        }
    )


# ============================================================
# AUTOMATION STATUS
# ============================================================

@app.route(
    "/automation-status",
    methods=["GET"]
)
def get_automation_status():

    return jsonify(
        automation_status
    )


# ============================================================
# START AUTOMATION
# ============================================================

@app.route(
    "/run-automation",
    methods=["GET", "POST"]
)
def trigger_automation():

    global automation_running

    # ========================================================
    # CHECK ENVIRONMENT
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
                "status":
                    "failed",

                "error":
                    "Missing required Render "
                    "environment variables.",

                "missing":
                    missing_variables
            }
        ), 500

    # ========================================================
    # CHECK IF ALREADY RUNNING
    # ========================================================

    if automation_running:

        return jsonify(
            {
                "status":
                    "already_running",

                "message":
                    "Automation is already running.",

                "check_status":
                    "/automation-status"
            }
        ), 202

    # ========================================================
    # LOCK AUTOMATION
    # ========================================================

    acquired = automation_lock.acquire(
        blocking=False
    )

    if not acquired:

        return jsonify(
            {
                "status":
                    "already_running",

                "message":
                    "Another automation process "
                    "is already running.",

                "check_status":
                    "/automation-status"
            }
        ), 202

    automation_running = True

    # ========================================================
    # START BACKGROUND THREAD
    # ========================================================

    thread = threading.Thread(
        target=run_automation_background,
        daemon=True
    )

    thread.start()

    # ========================================================
    # RETURN IMMEDIATELY
    # ========================================================

    return jsonify(
        {
            "status":
                "started",

            "message":
                "Automation started in the background.",

            "check_status":
                "/automation-status"
        }
    ), 202


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
        port=port,
        debug=False
    )
