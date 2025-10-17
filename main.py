import os, json, random, requests, argparse
from bs4 import BeautifulSoup
from gtts import gTTS
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -----------------------------
# ARGUMENTS
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument('--single', action='store_true', help='Post only one video')
args = parser.parse_args()

# -----------------------------
# CONFIGURATION
# -----------------------------
MOVIE_CLIPS_DIR = "movie_clips"
AUDIO_DIR = "audio"
VIDEOS_DIR = "videos"
POSTED_FILE = "posted_videos.json"

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO") or EMAIL_ADDRESS

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# -----------------------------
# UTILITY FUNCTIONS
# -----------------------------
def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r") as f:
            return json.load(f)
    return []

def save_posted(posted):
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f, ensure_ascii=False, indent=2)

def generate_tts(text, name):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    tts_path = os.path.join(AUDIO_DIR, f"audio_{name}.mp3")
    tts = gTTS(text=text, lang='te')
    tts.save(tts_path)
    return tts_path

def create_video(clip_path, caption, audio_path, name):
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    clip = VideoFileClip(clip_path).subclip(0, min(5, VideoFileClip(clip_path).duration))
    txt_clip = TextClip(caption, fontsize=30, color='white', font='Arial', method='caption', size=(clip.w, None), align='center')
    txt_clip = txt_clip.set_position(('center','bottom')).set_duration(clip.duration)
    audio_clip = AudioFileClip(audio_path)
    final_clip = CompositeVideoClip([clip, txt_clip]).set_audio(audio_clip)
    video_path = os.path.join(VIDEOS_DIR, f"video_{name}.mp4")
    final_clip.write_videofile(video_path, codec='libx264', audio_codec='aac', fps=24)
    return video_path

def post_to_instagram(video_path, caption):
    url_upload = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/media"
    files = {'file': open(video_path, 'rb')}
    data = {'caption': caption, 'access_token': ACCESS_TOKEN}
    response = requests.post(url_upload, files=files, data=data).json()
    if "id" not in response:
        print("Upload failed:", response)
        return None
    creation_id = response["id"]
    url_publish = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/media_publish"
    publish_data = {'creation_id': creation_id, 'access_token': ACCESS_TOKEN}
    publish_res = requests.post(url_publish, data=publish_data).json()
    return publish_res.get("id", None)

# -----------------------------
# DM FUNCTIONS
# -----------------------------
def load_dm_messages():
    return [
        "రా, ఈ అవకాశాన్ని చేజిక్కించుకో! 😎",
        "మరి check చేసావా?🔥 మనదే ఫస్ట్ క్లాస్ డీల్!",
        "నిన్ను వదుల్కో వద్దు! త్వరగా apply చేయు!"
    ]

def get_recent_followers():
    url = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/followers"
    params = {'access_token': ACCESS_TOKEN}
    response = requests.get(url, params=params).json()
    return [f["id"] for f in response.get("data", [])]

def send_dm(follower_id, message):
    url = f"https://graph.facebook.com/v24.0/{follower_id}/messages"
    params = {
        'recipient': json.dumps({'id': follower_id}),
        'message': json.dumps({'text': message}),
        'access_token': ACCESS_TOKEN
    }
    return requests.post(url, data=params).json()

# -----------------------------
# EMAIL FUNCTIONS
# -----------------------------
def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully")
    except Exception as e:
        print("Error sending email:", e)

# -----------------------------
# PROMOTION FUNCTIONS
# -----------------------------
def get_promotions():
    url = f"https://graph.facebook.com/v24.0/{IG_USER_ID}/conversations"
    params = {'access_token': ACCESS_TOKEN, 'fields': 'participants,messages{message,from}'}
    response = requests.get(url, params=params).json()
    promotions = []
    for conv in response.get('data', []):
        for msg in conv.get('messages', {}).get('data', []):
            if "promotion" in msg.get('message', '').lower() or "order" in msg.get('message', '').lower():
                promotions.append({'from': msg['from']['id'], 'message': msg['message']})
    return promotions

def respond_promotion(follower_id, reply_text="Thanks for your promotion request!"):
    url = f"https://graph.facebook.com/v24.0/{follower_id}/messages"
    params = {
        'recipient': json.dumps({'id': follower_id}),
        'message': json.dumps({'text': reply_text}),
        'access_token': ACCESS_TOKEN
    }
    return requests.post(url, data=params).json()

def email_promotions_summary(promotions):
    if not promotions:
        return
    body = "New promotions received:\n\n"
    for p in promotions:
        body += f"From ID: {p['from']}\nMessage: {p['message']}\n\n"
    send_email("Promotion Alert", body)

# -----------------------------
# JOB / INTERNSHIP SCRAPER
# -----------------------------
def fetch_internships():
    url = "https://internshala.com/internships/remote"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    internships = []
    for item in soup.find_all("div", class_="internship_meta"):
        title_tag = item.find("a", class_="profile")
        if not title_tag:
            continue
        title = title_tag.text.strip()
        company = item.find("a", class_="link_display_like_text").text.strip()
        location = item.find("div", class_="location_link").text.strip()
        internships.append({"title": title, "company": company, "location": location})
    return internships

def generate_job_caption(job):
    templates = [
        f"🔥 {job['title']} {job['company']} లో apply చేసుకో! {job['location']}",
        f"💼 కొత్త అవకాశం: {job['title']} - {job['company']} ({job['location']})",
        f"🚀 Telugu Job Alert: {job['title']} {job['company']} లో, apply చేయడం మర్చిపోకు!"
    ]
    return random.choice(templates)

# -----------------------------
# PIXABAY FUNCTIONS
# -----------------------------
def fetch_pixabay_clips(query="office, work, coding, study", num=5):
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={query}&per_page={num}&safesearch=true"
    response = requests.get(url).json()
    clips = []
    for hit in response.get("hits", []):
        video_url = hit['videos']['medium']['url']
        clips.append(video_url)
    return clips

def download_clip(url, save_dir=MOVIE_CLIPS_DIR):
    os.makedirs(save_dir, exist_ok=True)
    local_filename = os.path.join(save_dir, url.split("/")[-1].split("?")[0])
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    posted = load_posted()

    # Local movie clips
    local_clips = [os.path.join(MOVIE_CLIPS_DIR, f) for f in os.listdir(MOVIE_CLIPS_DIR) if f.endswith(('.mp4','.mov'))]

    # Pixabay clips
    pixabay_clips = fetch_pixabay_clips()
    num_videos = 1 if args.single else 2

    jobs = fetch_internships()

    for video_index in range(num_videos):
        job = random.choice(jobs)
        
        # Pick either local or Pixabay clip
        if random.random() < 0.5 and local_clips:
            clip_path = random.choice(local_clips)
        else:
            clip_path = download_clip(random.choice(pixabay_clips))

        unique_name = f"{video_index}_{random.randint(1000,9999)}"
        caption = generate_job_caption(job)
        audio_path = generate_tts(caption, unique_name)
        video_path = create_video(clip_path, caption, audio_path, unique_name)
        ig_post_id = post_to_instagram(video_path, caption)

        if ig_post_id:
            print(f"Posted video {video_path} to Instagram: {ig_post_id}")
            posted.append(clip_path)
            save_posted(posted)

            # DM automation
            dm_messages = load_dm_messages()
            followers = get_recent_followers()
            for follower_id in followers:
                dm_message = random.choice(dm_messages)
                send_dm(follower_id, dm_message)

            # Email summary
            subject = f"Instagram Automation: Video Posted"
            body = f"Video: {video_path}\nCaption: {caption}\nIG Post ID: {ig_post_id}\nDMs sent to {len(followers)} followers."
            send_email(subject, body)

            # Promotion handling
            promotions = get_promotions()
            for promo in promotions:
                respond_promotion(promo['from'])
            email_promotions_summary(promotions)

if __name__ == "__main__":
    main()