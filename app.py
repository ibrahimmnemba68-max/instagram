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
# GOOGLE DRIVE
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

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "drive_sync"
)

TRACKING_FILE = os.path.join(
    BASE_DIR,
    "posted_history.json"
)


# This will be discovered automatically.
INSTAGRAM_IMAGE_DIR = None


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
# CREATE DOWNLOAD DIRECTORY
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
# FIND CONTENT QUEUE
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


    matches = []


    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        normalized_root = os.path.normpath(root)

        parts = normalized_root.split(os.sep)


        if len(parts) >= 2:

            parent_name = parts[-2].lower()
            current_name = parts[-1].lower()


            if (
                parent_name == "instagram"
                and current_name == "content_queue"
            ):

                matches.append(root)


    if not matches:

        print(
            "❌ Instagram/Content_queue was not found."
        )

        print()
        print(
            "📂 Downloaded directory structure:"
        )


        for root, dirs, files in os.walk(
            DOWNLOAD_DIR
        ):

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


    selected = matches[0]


    print()
    print(
        "✅ Instagram/Content_queue found:"
    )

    print(selected)


    return selected


# ============================================================
# GOOGLE DRIVE SYNCHRONIZATION
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


    try:

        os.makedirs(
            DOWNLOAD_DIR,
            exist_ok=True
        )


        print()
        print(
            "📁 Google Drive folder:"
        )

        print(
            BRAIN_FOLDER_URL
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


                if os.path.isfile(full_path):

                    images.append(full_path)


        images.sort(
            key=lambda x:
            os.path.basename(x).lower()
        )


        print()
        print(
            f"📸 Found {len(images)} images."
        )


        for image in images:

            print(
                f"   🖼️ "
                f"{os.path.basename(image)}"
            )


        if not images:

            print()
            print(
                "❌ No images found in Content_queue."
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

        print(str(e))

        traceback.print_exc()

        return False


# ============================================================
# COMPILE KNOWLEDGE BASE
# ============================================================

def compile_knowledge_base():

    context_data = ""


    if not os.path.exists(DOWNLOAD_DIR):

        return context_data


    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        # Don't read image directory
        if INSTAGRAM_IMAGE_DIR:

            try:

                image_dir = os.path.abspath(
                    INSTAGRAM_IMAGE_DIR
                )

                current_root = os.path.abspath(
                    root
                )


                if (
                    current_root == image_dir
                    or current_root.startswith(
                        image_dir + os.sep
                    )
                ):

                    continue

            except Exception:

                pass


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
                    "\n"
                    f"--- Source File: {file} ---\n"
                    f"{content}\n"
                )


            except Exception as e:

                print(
                    f"⚠️ Could not read {file}: {e}"
                )


    return context_data


# ============================================================
# GET NEXT IMAGE
# ============================================================

def get_next_image():

    if not INSTAGRAM_IMAGE_DIR:

        return None


    if not os.path.isdir(
        INSTAGRAM_IMAGE_DIR
    ):

        return None


    valid_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    )


    history = load_history()


    all_images = []


    for filename in os.listdir(
        INSTAGRAM_IMAGE_DIR
    ):

        if filename.lower().endswith(
            valid_extensions
        ):

            full_path = os.path.join(
                INSTAGRAM_IMAGE_DIR,
                filename
            )


            if os.path.isfile(full_path):

                all_images.append(full_path)


    all_images.sort(
        key=lambda x:
        os.path.basename(x).lower()
    )


    if not all_images:

        return None


    # --------------------------------------------------------
    # Find an image that has not been posted
    # --------------------------------------------------------

    for image in all_images:

        if image not in history:

            return image


    # --------------------------------------------------------
    # All images have already been posted.
    #
    # Reset history so the queue can start again.
    # --------------------------------------------------------

    print()
    print(
        "🔄 All images have already been posted."
    )

    print(
        "🔄 Resetting posting history."
    )


    history = []

    save_history(history)


    return all_images[0]


# ============================================================
# POST IMAGE
# ============================================================

def post_image(cl, image_path):

    if not image_path:

        return (
            "Error: No image was selected."
        )


    if not os.path.exists(image_path):

        return (
            "Error: Image file does not exist."
        )


    filename = os.path.basename(
        image_path
    )


    print()
    print(
        "📸 Posting image:"
    )

    print(filename)


    try:

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
            f"Success: Image '{filename}' "
            "posted successfully."
        )


    except Exception as e:

        print()
        print(
            "❌ Image posting failed:"
        )

        print(str(e))

        traceback.print_exc()


        return (
            f"Error: Image posting failed: {e}"
        )


# ============================================================
# PROCESS IMAGE POST
# ============================================================

def process_and_post_image(cl):

    print()
    print(
        "================================================"
    )

    print(
        "📸 STARTING IMAGE POSTING"
    )

    print(
        "================================================"
    )


    if not INSTAGRAM_IMAGE_DIR:

        return (
            "Error: Instagram/Content_queue "
            "was not found."
        )


    image_path = get_next_image()


    if not image_path:

        return (
            "Error: No images found "
            "inside Instagram/Content_queue."
        )


    print()
    print(
        "🎯 Selected image:"
    )

    print(
        os.path.basename(image_path)
    )


    result = post_image(
        cl,
        image_path
    )


    # --------------------------------------------------------
    # Save image to history ONLY after successful posting
    # --------------------------------------------------------

    if result.startswith("Success:"):

        history = load_history()


        if image_path not in history:

            history.append(
                image_path
            )


        save_history(history)


        print()
        print(
            "✅ Image added to posting history."
        )


    return result


# ============================================================
# MONITOR COMMENTS
# ============================================================

def monitor_and_reply_to_comments(cl):

    if not ai_client:

        return (
            "Comment processor skipped: "
            "GEMINI_API_KEY is missing."
        )


    print()
    print(
        "================================================"
    )

    print(
        "💬 CHECKING INSTAGRAM COMMENTS"
    )

    print(
        "================================================"
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

        medias = cl.user_medias(
            user_id,
            amount=3
        )


        print()
        print(
            f"📱 Checking {len(medias)} recent posts."
        )


        # ----------------------------------------------------
        # Knowledge base
        # ----------------------------------------------------

        knowledge_context = (
            compile_knowledge_base()
        )


        if not knowledge_context:

            knowledge_context = (
                "No specific internal project "
                "knowledge is currently available."
            )


        reply_count = 0


        # ====================================================
        # POSTS
        # ====================================================

        for media in medias:

            try:

                comments = cl.media_comments(
                    media.id,
                    amount=20
                )


            except Exception as e:

                print()
                print(
                    f"⚠️ Could not read comments "
                    f"for media {media.id}: {e}"
                )

                continue


            # =================================================
            # COMMENTS
            # =================================================

            for comment in comments:

                try:

                    # -----------------------------------------
                    # Ignore our own comments
                    # -----------------------------------------

                    if not comment.user:

                        continue


                    commenter = (
                        comment.user.username
                    )


                    if commenter.lower() == USERNAME.lower():

                        continue


                    comment_text = (
                        comment.text or ""
                    ).strip()


                    if not comment_text:

                        continue


                    print()
                    print(
                        f"💬 @{commenter}:"
                    )

                    print(
                        comment_text
                    )


                    # -----------------------------------------
                    # AI PROMPT
                    # -----------------------------------------

                    ai_prompt = f"""
You are the official AI assistant for
{USERNAME}.

You help answer Instagram comments about
the project.

INTERNAL PROJECT KNOWLEDGE:

{knowledge_context}

INSTAGRAM COMMENT:

@{commenter} wrote:

"{comment_text}"

Write a short, natural and friendly reply.

Rules:

1. Use ONLY information contained in the internal
   project knowledge.
2. Never invent prices.
3. Never invent dates.
4. Never invent locations.
5. Never invent services or features.
6. Never make promises that are not in the knowledge.
7. If the information is not available, politely say
   that the team can provide more details.
8. Keep the reply conversational.
9. Maximum 2 short sentences.
10. Do not mention that you are reading a knowledge base.
"""


                    # -----------------------------------------
                    # Gemini
                    # -----------------------------------------

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
                            "⚠️ Gemini returned an empty reply."
                        )

                        continue


                    # -----------------------------------------
                    # Reply to comment
                    # -----------------------------------------

                    cl.comment_create(
                        media.id,
                        reply_text,
                        replied_to_comment_id=comment.id
                    )


                    reply_count += 1


                    print()
                    print(
                        f"🤖 Replied to @{commenter}:"
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
            "Comment checks completed. "
            f"Replies sent: {reply_count}."
        )


    except Exception as e:

        print()
        print(
            "⚠️ Comment processor failed:"
        )

        print(str(e))

        traceback.print_exc()


        return (
            f"Comment processor warning: {e}"
        )


# ============================================================
# BACKGROUND AUTOMATION
# ============================================================

def run_automation_background():

    global automation_running


    try:

        automation_status.update(
            {
                "status": "running",
                "message": "Automation is running.",
                "started_at":
                    datetime.utcnow().isoformat(),
                "finished_at": None,
                "posting_result": None,
                "comment_reply_result": None,
                "error": None
            }
        )


        print()
        print(
            "================================================"
        )

        print(
            "🏁 AUTOMATION STARTED"
        )

        print(
            "================================================"
        )


        # ====================================================
        # CHECK INSTAGRAM SESSION
        # ====================================================

        if not SESSION_ID:

            raise RuntimeError(
                "INSTAGRAM_SESSION_ID is missing."
            )


        # ====================================================
        # CHECK GEMINI
        # ====================================================

        if not GEMINI_API_KEY:

            raise RuntimeError(
                "GEMINI_API_KEY is missing."
            )


        # ====================================================
        # GOOGLE DRIVE
        # ====================================================

        automation_status[
            "message"
        ] = "Synchronizing Google Drive."


        drive_synced = (
            sync_google_drive()
        )


        if not drive_synced:

            raise RuntimeError(
                "Google Drive synchronization failed."
            )


        # ====================================================
        # INSTAGRAM CLIENT
        # ====================================================

        automation_status[
            "message"
        ] = "Logging into Instagram."


        print()
        print(
            "🔐 Logging into Instagram..."
        )


        cl = Client()


        cl.login_by_sessionid(
            SESSION_ID
        )


        # Verify account

        cl.user_id_from_username(
            USERNAME
        )


        print()
        print(
            "✅ Instagram authentication successful."
        )


        # ====================================================
        # POST IMAGE
        # ====================================================

        automation_status[
            "message"
        ] = "Posting image."


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

        automation_status[
            "message"
        ] = "Checking Instagram comments."


        comment_result = (
            monitor_and_reply_to_comments(
                cl
            )
        )


        automation_status[
            "comment_reply_result"
        ] = comment_result


        # ====================================================
        # FINISHED
        # ====================================================

        automation_status.update(
            {
                "status": "completed",

                "message":
                    "Automation completed successfully.",

                "finished_at":
                    datetime.utcnow().isoformat()
            }
        )


        print()
        print(
            "================================================"
        )

        print(
            "🎉 AUTOMATION COMPLETED"
        )

        print(
            "================================================"
        )


    except Exception as e:

        print()
        print(
            "================================================"
        )

        print(
            "❌ AUTOMATION FAILED"
        )

        print(
            str(e)
        )

        print(
            "================================================"
        )


        traceback.print_exc()


        automation_status.update(
            {
                "status": "failed",

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
                    "google_drive_sync": True,
                    "image_posting": True,
                    "reels": False,
                    "video_generation": False,
                    "instagram_music": False,
                    "gemini_comments": True
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
# RUN AUTOMATION
# ============================================================

@app.route(
    "/run-automation",
    methods=["GET", "POST"]
)
def trigger_automation():

    global automation_running


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
                "status": "failed",

                "error":
                    "Required Render environment "
                    "variables are missing.",

                "missing":
                    missing_variables
            }
        ), 500


    # ========================================================
    # CHECK CURRENT RUN
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
    # ACQUIRE LOCK
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
