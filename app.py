import os
import json
import threading
import traceback
from datetime import datetime, timezone

import gdown
from flask import Flask, jsonify
from instagrapi import Client
from google import genai


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = "fluentdome"

BRAIN_FOLDER_URL = (
    "https://drive.google.com/drive/folders/"
    "1xdraEwHizlHyZggtbl3o2zrpybzz8wUS?usp=sharing"
)

# Instagram Music track ID.
#
# IMPORTANT:
# A normal Instagram image/feed post cannot reliably be given
# an Instagram Music Library track through instagrapi.
#
# We keep this variable ready for the future Reel version.
INSTAGRAM_TRACK_ID = os.environ.get("INSTAGRAM_TRACK_ID")

TARGET_SONG_NAME = "Lofi Rain Instrumental"


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


os.makedirs(
    DOWNLOAD_DIR,
    exist_ok=True
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
# GEMINI
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
            f"❌ Gemini initialization failed: {e}"
        )

else:

    print(
        "⚠️ GEMINI_API_KEY is not configured."
    )


# ============================================================
# TIME
# ============================================================

def now_iso():

    return datetime.now(
        timezone.utc
    ).isoformat()


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

        print(
            "✅ Posting history saved."
        )

    except Exception as e:

        print(
            f"⚠️ Could not save history: {e}"
        )


# ============================================================
# FIND CONTENT QUEUE
# ============================================================

def find_content_queue():

    print()
    print(
        "🔎 Searching for Instagram/Content_queue..."
    )

    if not os.path.isdir(
        DOWNLOAD_DIR
    ):

        print(
            "❌ Download directory does not exist."
        )

        return None


    possible_matches = []


    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        normalized_root = os.path.normpath(
            root
        )

        parts = normalized_root.split(
            os.sep
        )

        if len(parts) < 2:

            continue


        parent_name = parts[-2].lower()

        current_name = parts[-1].lower()


        if (
            parent_name == "instagram"
            and current_name == "content_queue"
        ):

            possible_matches.append(
                root
            )


    if not possible_matches:

        print(
            "❌ Instagram/Content_queue was not found."
        )

        print()
        print(
            "📂 Current downloaded structure:"
        )


        for root, dirs, files in os.walk(
            DOWNLOAD_DIR
        ):

            level = root.replace(
                DOWNLOAD_DIR,
                ""
            ).count(
                os.sep
            )

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

    print(
        selected
    )


    if len(possible_matches) > 1:

        print(
            "⚠️ Multiple Content_queue folders found."
        )

        for match in possible_matches:

            print(
                f"   - {match}"
            )


    return selected


# ============================================================
# GOOGLE DRIVE SYNC
# ============================================================

def sync_google_drive():

    global INSTAGRAM_IMAGE_DIR


    print()
    print(
        "=============================================="
    )

    print(
        "📥 STARTING GOOGLE DRIVE SYNCHRONIZATION"
    )

    print(
        "=============================================="
    )


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
            "✅ Google Drive download finished."
        )


        INSTAGRAM_IMAGE_DIR = (
            find_content_queue()
        )


        if not INSTAGRAM_IMAGE_DIR:

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

                if os.path.isfile(
                    full_path
                ):

                    images.append(
                        full_path
                    )


        images.sort(
            key=lambda x:
                os.path.basename(x).lower()
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

            print(
                "❌ No images found."
            )

            return False


        print()
        print(
            "✅ Google Drive synchronization successful."
        )


        return True


    except Exception as e:

        print()
        print(
            "❌ Google Drive synchronization failed:"
        )

        print(
            str(e)
        )

        traceback.print_exc()

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

        # ----------------------------------------------------
        # Ignore Instagram image folder
        # ----------------------------------------------------

        if INSTAGRAM_IMAGE_DIR:

            try:

                image_dir = os.path.abspath(
                    INSTAGRAM_IMAGE_DIR
                )

                current_dir = os.path.abspath(
                    root
                )


                if (
                    current_dir == image_dir
                    or current_dir.startswith(
                        image_dir + os.sep
                    )
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
# POST IMAGE
# ============================================================

def post_image(
    cl,
    image_path
):

    if not os.path.exists(
        image_path
    ):

        return (
            "Error: Image file does not exist."
        )


    try:

        print()
        print(
            "📸 Posting image to Instagram..."
        )

        print(
            f"   {image_path}"
        )


        media = cl.photo_upload(
            path=image_path,
            caption=DEFAULT_CAPTION
        )


        print()
        print(
            "🎉 IMAGE POSTED SUCCESSFULLY!"
        )


        print(
            f"Media ID: {media.id}"
        )


        return (
            "Success: Image posted successfully."
        )


    except Exception as e:

        print()
        print(
            "❌ Image posting failed:"
        )

        print(
            str(e)
        )

        traceback.print_exc()


        return (
            f"Error: Image posting failed: {e}"
        )


# ============================================================
# PROCESS NEXT IMAGE
# ============================================================

def process_and_post_image(
    cl
):

    history = load_history()


    valid_exts = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    )


    if not INSTAGRAM_IMAGE_DIR:

        return (
            "Error: Instagram/Content_queue "
            "was not found."
        )


    if not os.path.isdir(
        INSTAGRAM_IMAGE_DIR
    ):

        return (
            "Error: Instagram/Content_queue "
            "directory does not exist."
        )


    all_images = []


    for filename in sorted(
        os.listdir(
            INSTAGRAM_IMAGE_DIR
        )
    ):

        if not filename.lower().endswith(
            valid_exts
        ):

            continue


        full_path = os.path.join(
            INSTAGRAM_IMAGE_DIR,
            filename
        )


        if os.path.isfile(
            full_path
        ):

            all_images.append(
                full_path
            )


    print()
    print(
        f"📸 Found {len(all_images)} images."
    )


    if not all_images:

        return (
            "Error: No valid images found."
        )


    # --------------------------------------------------------
    # Remove already posted images
    # --------------------------------------------------------

    unposted_images = [
        image
        for image in all_images
        if image not in history
    ]


    print(
        f"📊 Previously posted: "
        f"{len(all_images) - len(unposted_images)}"
    )

    print(
        f"📊 Remaining: "
        f"{len(unposted_images)}"
    )


    # --------------------------------------------------------
    # Reset after everything has been posted
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


    # --------------------------------------------------------
    # Select next image
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
    # Post
    # --------------------------------------------------------

    result = post_image(
        cl,
        target_image
    )


    # --------------------------------------------------------
    # Save only after successful post
    # --------------------------------------------------------

    if result.startswith(
        "Success:"
    ):

        if target_image not in history:

            history.append(
                target_image
            )


        save_history(
            history
        )


    return result


# ============================================================
# COMMENT MONITOR
# ============================================================

def monitor_and_reply_to_comments(
    cl
):

    if not ai_client:

        return (
            "Comment processor skipped: "
            "GEMINI_API_KEY is missing."
        )


    print()
    print(
        "💬 Scanning recent Instagram posts..."
    )


    try:

        # ----------------------------------------------------
        # Get account
        # ----------------------------------------------------

        user_id = cl.user_id_from_username(
            USERNAME
        )


        # ----------------------------------------------------
        # Get recent posts
        # ----------------------------------------------------

        user_medias = cl.user_medias(
            user_id,
            amount=5
        )


        print(
            f"📱 Found {len(user_medias)} recent posts."
        )


        # ----------------------------------------------------
        # Knowledge base
        # ----------------------------------------------------

        knowledge_context = (
            compile_knowledge_base()
        )


        if not knowledge_context:

            knowledge_context = (
                "No specific internal company "
                "knowledge is available."
            )


        # ----------------------------------------------------
        # Process posts
        # ----------------------------------------------------

        for media in user_medias:

            print()
            print(
                f"🔎 Checking comments "
                f"for media {media.id}"
            )


            try:

                comments = cl.media_comments(
                    media.id,
                    amount=20
                )

            except Exception as e:

                print(
                    f"⚠️ Could not read comments "
                    f"for {media.id}: {e}"
                )

                continue


            # ------------------------------------------------
            # Comments
            # ------------------------------------------------

            for comment in comments:

                try:

                    if not comment.text:

                        continue


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
                        f"💬 @{comment.user.username}:"
                    )

                    print(
                        comment.text
                    )


                    # ----------------------------------------
                    # Gemini prompt
                    # ----------------------------------------

                    ai_prompt = f"""
You are the official AI assistant
for {USERNAME}.

You are answering comments on Instagram.

INTERNAL KNOWLEDGE:
{knowledge_context}

INSTAGRAM COMMENT:
@{comment.user.username} wrote:

"{comment.text}"

INSTRUCTIONS:

1. Answer using ONLY the internal knowledge.
2. Never invent facts.
3. Never invent prices.
4. Never invent dates.
5. Never invent amenities.
6. Never invent availability.
7. Never make promises.
8. If the answer is not in the knowledge,
   politely say that the team can provide
   more details.
9. Be friendly and natural.
10. Maximum 2 short sentences.
11. Do not mention that you are an AI unless
    the user specifically asks.
"""


                    # ----------------------------------------
                    # Gemini
                    # ----------------------------------------

                    response = (
                        ai_client
                        .models
                        .generate_content(
                            model="gemini-2.5-flash",
                            contents=ai_prompt
                        )
                    )


                    reply_text = ""


                    if response.text:

                        reply_text = (
                            response.text.strip()
                        )


                    if not reply_text:

                        print(
                            "⚠️ Gemini returned "
                            "an empty response."
                        )

                        continue


                    # ----------------------------------------
                    # Reply
                    # ----------------------------------------

                    cl.comment_create(
                        media.id,
                        reply_text,
                        replied_to_comment_id=comment.id
                    )


                    print()
                    print(
                        "🤖 Reply sent:"
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

                    traceback.print_exc()

                    continue


        return (
            "Comment checks processed completely."
        )


    except Exception as e:

        print()
        print(
            "⚠️ Comment processor failed:"
        )

        print(
            str(e)
        )

        traceback.print_exc()


        return (
            f"Comment processor warning: {e}"
        )


# ============================================================
# AUTOMATION
# ============================================================

def run_automation_background():

    global automation_running


    try:

        automation_status.update(
            {
                "status": "running",
                "message": "Automation is running.",
                "started_at": now_iso(),
                "finished_at": None,
                "posting_result": None,
                "comment_reply_result": None,
                "error": None
            }
        )


        print()
        print(
            "=============================================="
        )

        print(
            "🏁 IMAGE INSTAGRAM AUTOMATION STARTED"
        )

        print(
            "=============================================="
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
        # INSTAGRAM LOGIN
        # ====================================================

        if not SESSION_ID:

            raise RuntimeError(
                "INSTAGRAM_SESSION_ID is missing."
            )


        print()
        print(
            "🔐 Logging into Instagram..."
        )


        cl = Client()


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

        posting_result = (
            process_and_post_image(
                cl
            )
        )


        automation_status[
            "posting_result"
        ] = posting_result


        # ====================================================
        # COMMENTS
        # ====================================================

        comment_result = (
            monitor_and_reply_to_comments(
                cl
            )
        )


        automation_status[
            "comment_reply_result"
        ] = comment_result


        # ====================================================
        # COMPLETE
        # ====================================================

        automation_status.update(
            {
                "status": "completed",

                "message":
                    "Image posting and comment "
                    "processing completed.",

                "finished_at":
                    now_iso()
            }
        )


        print()
        print(
            "=============================================="
        )

        print(
            "🎉 AUTOMATION COMPLETED"
        )

        print(
            "=============================================="
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
                "status": "failed",

                "message":
                    "Automation failed.",

                "finished_at":
                    now_iso(),

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
                    "google_drive_sync": True,
                    "image_posting": True,
                    "gemini_comments": True,
                    "video_generation": False,
                    "reels": False,
                    "instagram_music_for_reels": True
                },

            "automation":
                automation_status
        }
    )


# ============================================================
# STATUS
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
                "status": "failed",

                "error":
                    "Required Render environment "
                    "variables are missing.",

                "missing":
                    missing_variables
            }
        ), 500


    # ========================================================
    # CHECK RUNNING
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
    # LOCK
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
    # THREAD
    # ========================================================

    thread = threading.Thread(
        target=run_automation_background,
        daemon=True
    )


    thread.start()


    return jsonify(
        {
            "status":
                "started",

            "message":
                "Image automation started "
                "in the background.",

            "check_status":
                "/automation-status"
        }
    ), 202


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify(
        {
            "status": "healthy",
            "service": "instagram-image-automation"
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
        port=port,
        debug=False
    )
