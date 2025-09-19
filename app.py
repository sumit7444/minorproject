from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from model_stub import analyze_posts
import os
import tweepy
from dotenv import load_dotenv
import time
import random
from geopy.geocoders import Nominatim
import json
import traceback

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    template_folder=os.path.join(os.path.dirname(__file__), 'templates')
)
CORS(app)

geolocator = Nominatim(user_agent="disaster_app")

def random_latlon(region="any"):
    if region.lower() == "india":
        return round(random.uniform(8, 28), 4), round(random.uniform(68, 97), 4)
    elif region.lower() == "usa":
        return round(random.uniform(25, 49), 4), round(random.uniform(-125, -67), 4)
    else:
        return round(random.uniform(-30, 55), 4), round(random.uniform(-130, 150), 4)

def get_lat_lon(place_name):
    try:
        if place_name:
            loc = geolocator.geocode(place_name)
            if loc:
                return loc.latitude, loc.longitude
    except:
        pass
    return None, None

def calculate_severity(text):
    high_keywords = ["disaster", "emergency", "massive", "flood", "earthquake", "cyclone", "tsunami", "landslide"]
    medium_keywords = ["alert", "warning", "storm", "heavy rain", "fire", "evacuate"]
    text_lower = text.lower()
    if any(word in text_lower for word in high_keywords):
        return round(random.uniform(3.0, 4.0), 2)
    elif any(word in text_lower for word in medium_keywords):
        return round(random.uniform(2.0, 3.0), 2)
    else:
        return round(random.uniform(0.5, 1.5), 2)

@app.route("/")
def home():
    return render_template("index.html")

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json(force=True)
    posts = data.get('posts', [])
    keyword = data.get('keyword', '#flood')
    region = data.get('region', 'any')
    real = data.get('real', False)
    try:
        if real:
            print("📥 Reading live tweets from tweets.json...")
            live_posts = []
            try:
                with open("tweets.json", "r") as f:
                    for line in f:
                        if line.strip():
                            tweet_data = json.loads(line)
                            live_posts.append({
                                "text": tweet_data.get("text", ""),
                                "lat": None,
                                "lon": None,
                                "timestamp": int(time.time() * 1000),
                            })
                posts = live_posts
                print(f"📊 Found {len(posts)} tweets to analyze.")
            except FileNotFoundError:
                print("⚠️ tweets.json not found. Run stream_listener.py to collect data.")
                return jsonify({'posts': [], 'score': 0, 'error': 'No live data found.'}), 200
            except json.JSONDecodeError:
                print("Error decoding JSON from tweets.json.")
                return jsonify({'error': 'Error reading live data file.'}), 500

        for p in posts:
            if not p.get('lat') or not p.get('lon'):
                p['lat'], p['lon'] = random_latlon(region)
        result = analyze_posts(posts)
        out = {
            'posts': result['posts'],
            'score': result['score'],
            'neg': result['sentimentCounts']['neg'],
            'neu': result['sentimentCounts']['neu'],
            'pos': result['sentimentCounts']['pos'],
            'keywordFreq': result['keywordFreq'],
            'times': result['times']
        }
        return jsonify(out), 200
    except Exception as e:
        print(f"❌ Backend Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000, debug=True)