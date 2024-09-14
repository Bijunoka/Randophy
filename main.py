from flask import Flask, session, redirect, request, send_from_directory

from flask_session import Session
from redis import Redis
from urllib.parse import urlencode
import base64
from requests import post, get
import os
from time import time

CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
CLIENT_ID = os.environ.get("CLIENT_ID")

app = Flask(__name__)

SESSION_TYPE = 'redis'
SESSION_REDIS = Redis(host='db', port=6379)
app.config.from_object(__name__)
Session(app)

parms = {
    "response_type" : "code",
    "client_id" : CLIENT_ID,
    "scope" : "playlist-modify-private user-read-recently-played",
    "redirect_uri" : "http://localhost:5000/callback",
}

query = urlencode(parms)
print(query)

@app.route("/login")
def login():
    return redirect("https://accounts.spotify.com/authorize?" + query)

@app.route("/callback")
def callback():
    code = request.args.get("code")

    url_token = "https://accounts.spotify.com/api/token"

    headers_token = {
        'Content-type': "application/x-www-form-urlencoded", 
        'Authorization': "Basic " + base64.b64encode((CLIENT_ID + ":" + CLIENT_SECRET).encode()).decode()
    }
    data_token = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:5000/callback",
    }
    r = post(url_token, headers=headers_token, data=data_token).json()
    if "access_token" not in r or "refresh_token" not in r:
        return redirect("/")
    session["access_token"] = r["access_token"]
    session["refresh_token"] = r["refresh_token"]
    return redirect("/")

@app.route('/', defaults={'filename': 'index.html'})
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route("/recommendations")
def recommendations():
    return api_requests("recommendations")

@app.route("/recently-played")
def recently_played():
    return api_requests("me/player/recently-played")

@app.route("/search")
def search():
    return api_requests("search")

@app.route("/<user_id>/playlists")
def user_playlists(user_id):
    return api_requests("users/" + user_id + "/playlists")
    
RATE_LIMIT = 5
TIME_WINDOW = 10

def api_requests(url, nbr=1):
    if "times" not in session:
        session["times"] = []
    times = session["times"]
    now = time()
    times = [t for t in times if now - t < TIME_WINDOW]
    times.append(now)
    session["times"] = times
    if len(times) >= RATE_LIMIT:
        return { "error": "rate limited" }

    if "access_token" not in session or "refresh_token" not in session:
        return {"error": "not logged in"}
    args = request.args
    url = "https://api.spotify.com/v1/" + url + "?" + urlencode(args)
    headers = {
        "Authorization": "Bearer " + session["access_token"]
    }
    r = get(url, headers=headers).json()
    if "error" in r:
        if r["error"]["message"] == "The access token expired" and nbr > 0:
            data_refresh = {
                "grant_type": "refresh_token",
                "refresh_token": session["refresh_token"],
                "client_id": CLIENT_ID,
            }
            headers_refresh = {
                'Content-type': "application/x-www-form-urlencoded",
                'Authorization': "Basic " + base64.b64encode((CLIENT_ID + ":" + CLIENT_SECRET).encode()).decode(),
            }
            r3 = post("https://accounts.spotify.com/api/token", headers=headers_refresh, data=data_refresh).json()
            print(r3)
            if "access_token" not in r3 or "refresh_token" not in r3:
                session.clear()
                return {"error": "Petit escroc va !"}
            session["access_token"] = r3["access_token"]
            session["refresh_token"] = r3["refresh_token"]
            print("refresh" + str(nbr))
            return api_requests(url, nbr-1)
    return r

app.run(host="0.0.0.0", port=5000)