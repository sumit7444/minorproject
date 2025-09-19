from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from model_stub import analyze_posts
import os
import tweepy
from dotenv import load_dotenv
import time
import random
from geopy.geocoders import Nominatim

# Load .env variables
load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
print("✅ Token Loaded:", bool(BEARER_TOKEN))  # Debug 1 — True means token mil gaya

# Flask app setup
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    template_folder=os.path.join(os.path.dirname(__file__), 'templates')
)
CORS(app)

# Geopy setup
geolocator = Nominatim(user_agent="disaster_app")

# Random Lat/Lon generator
def random_latlon(region="any"):
    if region.lower() == "india":
        return round(random.uniform(8, 28), 4), round(random.uniform(68, 97), 4)
    elif region.lower() == "usa":
        return round(random.uniform(25, 49), 4), round(random.uniform(-125, -67), 4)
    else:  # any/global
        return round(random.uniform(-30, 55), 4), round(random.uniform(-130, 150), 4)

# Location finder
def get_lat_lon(place_name):
    try:
        if place_name:
            loc = geolocator.geocode(place_name)
            if loc:
                return loc.latitude, loc.longitude
    except:
        pass
    return None, None

# Severity calculation based on keywords
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
            if not BEARER_TOKEN:
                return jsonify({"error": "Bearer token not found in .env"}), 500

            print("📥 Keyword Used:", keyword)  # Debug 2

            client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)
            query = f"{keyword} -is:retweet lang:en"
            tweets = client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["geo"],
                expansions=["geo.place_id", "author_id"],
                user_fields=["location"],
                place_fields=["full_name"]
            )

            tweet_count = len(tweets.data) if tweets.data else 0
            print("📊 Tweets Count:", tweet_count)  # Debug 3

            if tweet_count > 0:
                print("📝 First Tweet Text:", tweets.data[0].text)  # Debug 4

            posts = []
            if tweets.data:
                places = {p["id"]: p for p in tweets.includes.get("places", [])} if hasattr(tweets, "includes") else {}
                users = {u["id"]: u for u in tweets.includes.get("users", [])} if hasattr(tweets, "includes") else {}

                for t in tweets.data:
                    lat, lon = None, None

                    if hasattr(t, 'geo') and t.geo:
                        place_id = t.geo.get('place_id')
                        if place_id and place_id in places:
                            lat, lon = get_lat_lon(places[place_id].full_name)
                    elif hasattr(t, 'place') and t.place:
                        lat, lon = get_lat_lon(t.place.full_name)
                    elif t.author_id in users and users[t.author_id].location:
                        lat, lon = get_lat_lon(users[t.author_id].location)

                    if not lat or not lon:
                        lat, lon = random_latlon(region)

                    posts.append({
                        "text": t.text,
                        "lat": lat,
                        "lon": lon,
                        "timestamp": int(time.time() * 1000),
                        "severity": calculate_severity(t.text)
                    })

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
        print("❌ Backend Error:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000, debug=True)