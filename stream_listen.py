import tweepy
import os
import json
from dotenv import load_dotenv

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
OUTPUT_FILE = "tweets.json"

class TweetStreamer(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        tweet_data = {'text': tweet.text}
        print(f"✅ Received Tweet: {tweet.text[:50]}...")
        with open(OUTPUT_FILE, "a") as f:
            f.write(json.dumps(tweet_data) + "\n")

    def on_error(self, status_code):
        print(f"❌ An error has occurred: {status_code}")
        if status_code == 429:
            return False

if __name__ == "__main__":
    streamer = TweetStreamer(bearer_token=BEARER_TOKEN)
    print("🚀 Streamer created. Managing rules...")

    existing_rules = streamer.get_rules().data or []
    if existing_rules:
        rule_ids = [rule.id for rule in existing_rules]
        streamer.delete_rules(rule_ids)
        print(f"🧹 Cleared {len(rule_ids)} old rule(s).")

    keyword = "#earthquake"
    rule = tweepy.StreamRule(f"{keyword} -is:retweet lang:en")
    streamer.add_rules(rule)
    print(f"룰 Added new rule: '{rule.value}'")

    print("🎧 Listening for tweets... (Press Ctrl+C to stop)")
    streamer.filter()