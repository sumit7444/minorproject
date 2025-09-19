# model_stub.py
import re
from collections import defaultdict
from datetime import datetime
import math

# tiny lexicons & weights
DISASTER_WEIGHTS = {
    'flood': 2.0, 'cyclone': 2.0, 'earthquake': 3.0, 'wildfire': 2.0,
    'landslide': 2.0, 'drought': 1.5, 'collapse': 3.0, 'fire': 1.8, 'storm':1.5
}
NEG_WORDS = ['flood','storm','collapsed','collapse','evacu','injur','death','dead','missing','drought','fire','wildfire','landslide','outage','smoke','bridge collapse','destroyed']
POS_WORDS = ['safe','relief','arriv','under control','cleared','help','volunteer','minor']

def simple_sentiment(text):
    t = text.lower()
    score = 0
    hits = 0
    for w in NEG_WORDS:
        if w in t:
            score -= 1
            hits += 1
    for w in POS_WORDS:
        if w in t:
            score += 1
            hits += 1
    if hits == 0: return 0.0
    return score / hits  # -1 .. +1

def detect_keywords(text):
    t = text.lower()
    found = {}
    for k,w in DISASTER_WEIGHTS.items():
        if k in t:
            found[k] = found.get(k,0) + w
    return found

def analyze_posts(posts):
    """posts: list of {text, lat, lon, timestamp}
       returns dict with:
         posts (with severity, disaster_type, confidence),
         score (0-100), times (timeseries), sentimentCounts, keywordFreq
    """
    details = []
    keywordFreq = defaultdict(int)
    sentimentCounts = {'neg':0,'neu':0,'pos':0}
    total_sev = 0.0

    for p in posts:
        text = p.get('text','')
        s = simple_sentiment(text)
        keys = detect_keywords(text)
        severity = sum(keys.values())
        # sentiment influence
        if s < -0.3: severity += 1.2
        if s > 0.3: severity = max(0, severity - 0.6)
        severity = round(max(0, severity), 2)

        # pick disaster type
        if keys:
            disaster_type = max(keys.items(), key=lambda x:x[1])[0]
        else:
            disaster_type = 'Unknown'

        # confidence heuristic: scaled by severity and presence of keywords
        conf = min(0.99, 0.4 + min(1.0, severity / 4.0))
        conf = round(conf, 2)

        # timestamp normalize
        ts = p.get('timestamp')
        try:
            # accept unix ms or ISO string
            if isinstance(ts, (int,float)):
                tval = int(ts)
            else:
                # try parse ISO-ish
                dt = datetime.fromisoformat(ts)
                tval = int(dt.timestamp()*1000)
        except Exception:
            tval = int(datetime.utcnow().timestamp()*1000)

        detail = {
            'text': text, 'lat': p.get('lat'), 'lon': p.get('lon'),
            'timestamp': tval, 'severity': severity,
            'disaster_type': disaster_type, 'confidence': conf
        }
        details.append(detail)

        for k in keys:
            keywordFreq[k] += 1

        if s < -0.3: sentimentCounts['neg'] += 1
        elif s > 0.3: sentimentCounts['pos'] += 1
        else: sentimentCounts['neu'] += 1

        total_sev += severity

    # timeseries: aggregate by hour
    groups = {}
    for d in details:
        hour = int(d['timestamp'] // (1000*60*60))
        if hour not in groups: groups[hour] = {'sum':0,'count':0}
        groups[hour]['sum'] += d['severity']; groups[hour]['count'] += 1
    times = []
    for h in sorted(groups.keys()):
        times.append({'time': h*60*60*1000, 'avgSeverity': round(groups[h]['sum']/groups[h]['count'],2)})

    avg_raw = (total_sev / max(1, len(details)))
    score = min(100, int(round(avg_raw * 25)))  # scale to 0-100 roughly

    return {
        'posts': details,
        'score': score,
        'times': times,
        'sentimentCounts': sentimentCounts,
        'keywordFreq': dict(keywordFreq)
    }