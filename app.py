import os
import json
import threading
import traceback
from datetime import datetime

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
# GOOGLE DRIVE BRAIN
# ============================================================

BRAIN_FOLDER_URL = (
    "https://drive.google.com/drive/folders/"
    "1xdraEwHizlHyZggtbl3o2zrpybzz8wUS?usp=sharing"
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

# IMPORTANT:
# This is discovered automatically after Google Drive sync.
# We do NOT hard-code:
# drive_sync/new_brain/new_brain/Instagram/Content_queue
#
# This makes the program work even if the folder nesting changes.

INSTAGRAM_IMAGE_DIR = None


OUTPUT_VIDEO = os.path.join(
    BASE_DIR,
    "generated_reel.mp4"
)

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

        print(
            "✅ Gemini client initialized."
        )

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
# FIND INSTAGRAM CONTENT QUEUE
# ============================================================

def find_content_queue():

    """
    Search recursively inside DOWNLOAD_DIR for:

        Instagram/Content_queue

    This handles structures such as:

        drive_sync/Instagram/Content_queue

    or:

        drive_sync/new_brain/Instagram/Content_queue

    or:

        drive_sync/new_brain/new_brain/Instagram/Content_queue
    """

    if not os.path.isdir(
        DOWNLOAD_DIR
    ):

        return None


    for root, dirs, files in os.walk(
        DOWNLOAD_DIR
    ):

        normalized_root = os.path.normpath(
            root
        )

        parts = normalized_root.split(
            os.sep
        )


        if len(parts) >= 2:

            if (
                parts[-2].lower()
                == "instagram"
                and
                parts[-1].lower()
                == "content_queue"
            ):

                return root


    return None


# ============================================================
# GOOGLE DRIVE SYNC
# ============================================================

def sync_google_drive():

    global INSTAGRAM_IMAGE_DIR


    print()

    print(
        "📥 Starting Google Drive synchronization..."
    )

    print(
        "📁 Drive folder:"
    )

    print(
        BRAIN_FOLDER_URL
    )


    try:

        os.makedirs(
            DOWNLOAD_DIR,
            exist_ok=True
        )


        # ----------------------------------------------------
        # Download entire public Drive folder
        # ----------------------------------------------------

        downloaded = gdown.download_folder(
            url=BRAIN_FOLDER_URL,
            output=DOWNLOAD_DIR,
            quiet=False,
            remaining_ok=True
        )


        print()

        print(
            "📦 Google Drive download process finished."
        )


        # ----------------------------------------------------
        # Find Content_queue automatically
        # ----------------------------------------------------

        INSTAGRAM_IMAGE_DIR = find_content_queue()


        if not INSTAGRAM_IMAGE_DIR:

            print(
                "❌ Instagram/Content_queue was not found."
            )

            print()

            print(
                "🔎 Searching downloaded folders..."
            )


            for root, dirs, files in os.walk(
                DOWNLOAD_DIR
            ):

                print(
                    f"   {root}"
                )


            return False


        print()

        print(
            "📸 Instagram content queue found:"
        )

        print(
            INSTAGRAM_IMAGE_DIR
        )


        # ----------------------------------------------------
        # Count images
        # ----------------------------------------------------

        image_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        )


        image_count = 0


        for filename in os.listdir(
            INSTAGRAM_IMAGE_DIR
        ):

            if filename.lower().endswith(
                image_extensions
            ):

                image_count += 1


        print()

        print(
            f"📸 Content queue contains "
            f"{image_count} images."
        )


        if image_count < 3:

            print(
                "❌ At least 3 images are required."
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
        # Skip image directory
        # ----------------------------------------------------

        if (
            INSTAGRAM_IMAGE_DIR
            and
            os.path.abspath(root).startswith(
                os.path.abspath(
                    INSTAGRAM_IMAGE_DIR
                )
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
                    f"\n"
                    f"--- Source File: {file} ---\n"
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

def create_reel_video(
    target_images
):

    print()

    print(
        "🎬 Creating Instagram Reel..."
    )


    for image in target_images:

        print(
            f"   📷 {os.path.basename(image)}"
        )


    clips = []

    video = None


    try:

        # ----------------------------------------------------
        # Create image clips
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Combine clips
        # ----------------------------------------------------

        video = concatenate_videoclips(
            clips,
            method="compose"
        )


        # ----------------------------------------------------
        # Export
        # ----------------------------------------------------

        video.write_videofile(
            OUTPUT_VIDEO,
            fps=24,
            codec="libx264",
            audio=False,
            logger=None
        )


        print()

        print(
            "✅ Reel created:"
        )

        print(
            OUTPUT_VIDEO
        )


        return True


    except Exception as e:

        print(
            f"❌ Video creation failed: {e}"
        )

        traceback.print_exc()

        return False


    finally:

        try:

            if video:

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

        print()

        print(
            "🎵 Fetching Instagram track:"
        )

        print(
            TARGET_SONG_NAME
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
            "Error: Generated video does not exist."
        )


    track = get_music_track(
        cl
    )


    try:

        print()

        print(
            "🚀 Uploading Reel..."
        )


        # ====================================================
        # TRY MUSIC
        # ====================================================

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
                    "⚠️ Music upload failed:"
                )

                print(
                    str(music_error)
                )

                print(
                    "🔄 Trying normal Reel upload..."
                )


        # ====================================================
        # NORMAL REEL UPLOAD
        # ====================================================

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

        traceback.print_exc()


        return (
            f"Error: Reel upload failed: {e}"
        )


# ============================================================
# PROCESS IMAGES
# ============================================================

def process_and_post_slideshow(
    cl
):

    history = load_history()


    valid_exts = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    )


    # ========================================================
    # CHECK CONTENT QUEUE
    # ========================================================

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


    # ========================================================
    # FIND IMAGES
    # ========================================================

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
            "Error: No valid images found inside "
            "Instagram/Content_queue."
        )


    # ========================================================
    # REMOVE POSTED IMAGES
    # ========================================================

    unposted_images = [
        image
        for image in all_images
        if image not in history
    ]


    # ========================================================
    # RESET HISTORY WHEN NEEDED
    # ========================================================

    if len(unposted_images) < 3:

        print(
            "🔄 Fewer than 3 unposted images remain."
        )

        print(
            "🔄 Resetting posting history."
        )


        history = []

        unposted_images = all_images


    if len(unposted_images) < 3:

        return (
            "Error: At least 3 images are required "
            "to create a Reel."
        )


    # ========================================================
    # SELECT THREE IMAGES
    # ========================================================

    target_images = unposted_images[:3]


    print()

    print(
        "🎯 Selected images:"
    )


    for image in target_images:

        print(
            f"   - {os.path.basename(image)}"
        )


    # ========================================================
    # CREATE VIDEO
    # ========================================================

    video_created = create_reel_video(
        target_images
    )


    if not video_created:

        return (
            "Error: Could not create Reel video."
        )


    # ========================================================
    # UPLOAD
    # ========================================================

    upload_result = upload_reel(
        cl
    )


    # ========================================================
    # SAVE HISTORY ONLY AFTER SUCCESS
    # ========================================================

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


    # ========================================================
    # DELETE GENERATED VIDEO
    # ========================================================

    if os.path.exists(
        OUTPUT_VIDEO
    ):

        try:

            os.remove(
                OUTPUT_VIDEO
            )

            print(
                "🧹 Temporary generated video removed."
            )

        except Exception as e:

            print(
                f"⚠️ Could not remove video: {e}"
            )


    return upload_result


# ============================================================
# MONITOR COMMENTS
# ============================================================

def monitor_and_reply_to_comments(
    cl
):

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
                "No specific internal company notes "
                "are available. Reply politely as a "
                "helpful assistant."
            )


        # ====================================================
        # PROCESS POSTS
        # ====================================================

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


            # =================================================
            # PROCESS COMMENTS
            # =================================================

            for comment in comments:

                try:

                    # -----------------------------------------
                    # Ignore own comments
                    # -----------------------------------------

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


                    # -----------------------------------------
                    # Gemini prompt
                    # -----------------------------------------

                    ai_prompt = f"""
You are the AI operations representative
for the platform "{USERNAME}".

Below is the internal project knowledge:

{knowledge_context}

A user @{comment.user.username}
left this Instagram comment:

"{comment.text}"

Write a short, natural and friendly reply.

Rules:

1. Use only facts contained in the knowledge above.
2. Do not invent prices, dates, locations, features,
   promises or other information.
3. If the knowledge does not contain an answer,
   politely say that the team can provide more details.
4. Do not sound robotic.
5. Maximum 2 short sentences.
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

                        continue


                    # -----------------------------------------
                    # Reply
                    # -----------------------------------------

                    cl.comment_create(
                        media.id,
                        reply_text,
                        replied_to_comment_id=comment.id
                    )


                    print(
                        f"🚀 Replied to "
                        f"@{comment.user.username}:"
                    )

                    print(
                        reply_text
                    )


                except Exception as comment_error:

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
                "message": "Automation is running.",
                "started_at": datetime.utcnow().isoformat(),
                "finished_at": None,
                "posting_result": None,
                "comment_reply_result": None,
                "error": None
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

        drive_synced = sync_google_drive()


        if not drive_synced:

            raise RuntimeError(
                "Google Drive synchronization failed."
            )


        # ====================================================
        # INSTAGRAM CLIENT
        # ====================================================

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
        # POST REEL
        # ====================================================

        posting_log = (
            process_and_post_slideshow(
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
                "status": "completed",
                "message": "Automation completed successfully.",
                "finished_at": datetime.utcnow().isoformat()
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
                "status": "failed",
                "message": "Automation failed.",
                "finished_at": datetime.utcnow().isoformat(),
                "error": str(e)
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
                "Bridge Engine",

            "status":
                "online",

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
                "status": "failed",

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
                "status": "already_running",

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
                "status": "already_running",

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
            "status": "started",

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
