import os
import json
import gdown
from flask import Flask, jsonify
from instagrapi import Client
from moviepy import ImageClip, concatenate_videoclips

from google import genai

app = Flask(__name__)

# --- SECURE CREDENTIALS (FETCHED FROM RENDER ENV) ---
USERNAME = "fluentdome"

# ⚠️ Make sure this is a real, numeric track ID string from Instagram
TARGET_SONG_NAME = "Lofi Rain Instrumental"   

# Sensitive tokens are pulled dynamically from system environments
SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Restored your exact Google Drive brain link
BRAIN_FOLDER_URL = "https://google.com"

# Folder directory mapping layouts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "drive_sync")
INSTAGRAM_IMAGE_DIR = os.path.join(DOWNLOAD_DIR, "Instagram")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "generated_reel.mp4")

TRACKING_FILE = os.path.join(BASE_DIR, "posted_history.json")
DEFAULT_CAPTION = "Automated post from my synchronized project brain database! 🧠🤖 #fluentdome"

# Ensure runtime paths exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize Gemini Client safely using your environment variable
ai_client = None
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)

# --- SYSTEM UTILITIES ---

def load_history():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_history(history):
    with open(TRACKING_FILE, "w") as f: json.dump(history, f, indent=4)

def sync_google_drive():
    """Downloads the entire Obsidian vault directory context from Google Drive."""
    print("📥 Commencing recursive database download from Google Drive...")
    try:
        gdown.download_folder(url=BRAIN_FOLDER_URL, output=DOWNLOAD_DIR, quiet=True, remaining_ok=True)
        print("✅ Google Drive asset sync completed.")
    except Exception as e:
        print(f"⚠️ Drive sync encountered warnings: {e}")

def compile_knowledge_base():
    """Scans all downloaded text and note markdown files to form an AI brain text block."""
    context_data = ""
    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.endswith((".txt", ".md")) and "Instagram" not in root:
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        context_data += f"\n--- Source File: {file} ---\n" + f.read()
                except:
                    continue
    return context_data

# --- CORE ROUTINE AUTOMATIONS ---

def process_and_post_slideshow(cl):
    """Handles image selection, rotation logic, video assembly, and posting."""
    history = load_history()
    valid_exts = (".jpg", ".jpeg", ".png")
    
    if not os.path.exists(INSTAGRAM_IMAGE_DIR):
        return "Error: Sync completed but 'Instagram' media queue subfolder was not found."

    all_images = [os.path.join(INSTAGRAM_IMAGE_DIR, f) for f in sorted(os.listdir(INSTAGRAM_IMAGE_DIR)) if f.lower().endswith(valid_exts)]
    
    if not all_images:
        return "Error: No valid images found inside your Instagram cloud folder directory."

    # Infinite Shuffle Rotation Logic Block
    unposted_images = [img for img in all_images if img not in history]
    
    if len(unposted_images) < 3:
        print("🔄 All available images exhausted! Wiping tracking logs to shuffle cycle...")
        history = []
        unposted_images = all_images

    target_images = unposted_images[:3]

    print(f"🎬 Merging targets: {[os.path.basename(x) for x in target_images]}")
    clips = [ImageClip(img).set_duration(3) for img in target_images]
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile(OUTPUT_VIDEO, fps=24, codec="libx264", logger=None)

    # FIXED: Official instagrapi syntax to lookup music track objects
    print(f"Fetching official audio track info for ID: {INSTAGRAM_TRACK_ID}...")
    try:
        track_info = cl.track_info(INSTAGRAM_TRACK_ID)
        print(f"Loaded track title: {track_info.title}")
    except Exception as e:
        return f"Error: Failed to fetch Instagram track info: {e}"

    # FIXED: Official instagrapi syntax to deploy videos with linked tracks
    try:
        print("🚀 Uploading video reel with linked track payload...")
        media = cl.clip_upload(
            path=OUTPUT_VIDEO,
            caption=DEFAULT_CAPTION,
            track=track_info
        )
        print("🎉 SUCCESS! Video posted live.")
    except Exception as e:
        return f"Error: Video conversion worked, but upload stream failed: {e}"

    # Save to history file logs
    for img in target_images:
        history.append(img)
    save_history(history)
    return "Success: Video generated and deployed live with music tracks."

def monitor_and_reply_to_comments(cl):
    """Fetches new comments on recent posts and uses Gemini to answer them using your notes."""
    if not ai_client:
        return "Comment processor skipped: Gemini API Key missing."

    print("💬 Scanning recent media timeline for comment notifications...")
    try:
        user_id = cl.user_id_from_username(USERNAME)
        user_medias = cl.user_medias(user_id, amount=3)
        
        knowledge_context = compile_knowledge_base()
        if not knowledge_context:
            knowledge_context = "No specific internal company notes available. Reply politely as a helpful AI assistant."

        for media in user_medias:
            comments = cl.media_comments(media.id, amount=10)
            for comment in comments:
                if comment.user.username == USERNAME:
                    continue
                
                # Check if thread already has been processed
                if hasattr(comment, 'has_liked') and comment.has_liked:
                    continue

                print(f"Prompting Gemini for comment: '{comment.text}' from user @{comment.user.username}")
                
                ai_prompt = f"""
                You are the AI operations representative for the platform '{USERNAME}'.
                Below is the knowledge database derived directly from our project vault files:
                {knowledge_context}
                
                User @{comment.user.username} left this comment on our post:
                "{comment.text}"
                
                Formulate a short, natural, friendly reply answering their statement using exclusively the facts provided above. Do not sound robotic. Max 2 short sentences.
                """
                
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=ai_prompt,
                )
                
                reply_text = response.text.strip()
                cl.comment_create(media.id, reply_text, replied_to_comment_id=comment.id)
                print(f"🚀 Sent reply to @{comment.user.username}: {reply_text}")
                
        return "Comment checks processed completely."
    except Exception as e:
        return f"Comment processor warning: {e}"

# --- FLASK ENDPOINTS ---

@app.route('/')
def home():
    return jsonify({"system": "Autonomous Obsidian-to-Instagram Bridge Engine Active"})

@app.route('/run-automation', methods=['GET', 'POST'])
def trigger_automation():
    """Endpoint target hit by your robot every 2 days to execute the core processes."""
    if not SESSION_ID or not GEMINI_API_KEY:
        return jsonify({"status": "Failed", "error": "System variables missing inside Render Environment Settings."})

    print("\n🏁 Autonomous routine checklist initiated...")
    sync_google_drive()
    
    cl = Client()
    try:
        cl.login_by_sessionid(SESSION_ID)
        cl.user_id_from_username(USERNAME)
    except Exception as e:
        return jsonify({"status": "Failed", "error": f"Instagram Authentication Blocked: {e}"})

    posting_log = process_and_post_slideshow(cl)
    comment_log = monitor_and_reply_to_comments(cl)

    return jsonify({
        "status": "Complete",
        "posting_result": posting_log,
        "comment_reply_result": comment_log
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
