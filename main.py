from flask import Flask, session, redirect, request, send_from_directory
from urllib.parse import urlencode
from flask_session import Session
from requests import post, get
from redis import Redis
from time import time
import base64, os

RATE_LIMIT = 5
TIME_WINDOW = 10

CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
CLIENT_ID = os.environ.get("CLIENT_ID")
URL = os.environ.get("URL")
APP_AUTH = "Basic " + base64.b64encode((CLIENT_ID + ":" + CLIENT_SECRET).encode()).decode()

DEFAULT_URL = "https://api.spotify.com/v1/"

app = Flask(__name__)

SESSION_TYPE = 'redis'
SESSION_REDIS = Redis(host='db', port=6379)
app.config.from_object(__name__)
Session(app)

@app.route("/login")
def login():
    parms = {
        "response_type" : "code",
        "client_id" : CLIENT_ID,
        "scope" : "playlist-modify-private user-read-recently-played",
        "redirect_uri" : URL + "/callback",
    }
    return redirect("https://accounts.spotify.com/authorize?" + urlencode(parms))

@app.route("/callback")
def callback():
    code = request.args.get("code")
    url = "https://accounts.spotify.com/api/token"
    headers = {
        'Content-type': "application/x-www-form-urlencoded", 
        'Authorization': APP_AUTH
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": URL + "/callback",
    }
    response = post(url, headers=headers, data=data).json()
    if "access_token" not in response or "refresh_token" not in response:
        return redirect("/")
    session["access_token"] = response["access_token"]
    session["refresh_token"] = response["refresh_token"]
    return redirect("/")

@app.route('/', defaults={'filename': 'index.html'})
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route("/recommendations")
def recommendations():
    return api_requests(DEFAULT_URL + "recommendations")

@app.route("/recently-played")
def recently_played():
    return api_requests(DEFAULT_URL + "me/player/recently-played")

@app.route("/search")
def search():
    return api_requests(DEFAULT_URL + "search")

@app.route("/<user_id>/playlists")
def user_playlists(user_id):
    return api_requests(DEFAULT_URL + "users/" + user_id + "/playlists")

@app.route("/oembed")
def oembed():
    return api_requests("https://open.spotify.com/oembed")

@app.route("/me")
def me():
    return api_requests(DEFAULT_URL + "me")

def api_requests(url, nbr=1):
    # Rate limiting
    if "times" not in session:
        session["times"] = []
    times = session["times"]
    now = time()
    times = [t for t in times if now - t < TIME_WINDOW]
    times.append(now)
    session["times"] = times
    if len(times) >= RATE_LIMIT:
        return { "error": "rate limited" }

    # Check if logged in
    if "access_token" not in session or "refresh_token" not in session:
        return {"error": "not logged in"}
    
    # Make the request to the Spotify API
    url = url + "?" + urlencode(request.args)
    response = get(url, headers={"Authorization": "Bearer " + session["access_token"]}).json()

    # Refresh token if needed
    if nbr > 0 and "error" in response and response["error"]["message"] == "The access token expired":
        refresh_url = "https://accounts.spotify.com/api/token"
        headers = {
            'Content-type': "application/x-www-form-urlencoded",
            'Authorization': APP_AUTH,
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": session["refresh_token"],
            "client_id": CLIENT_ID,
        }
        response = post(refresh_url, headers=headers, data=data).json()
        print(response)
        if "access_token" not in response or "refresh_token" not in response:
            session.clear()
            return {"error": "Petit escroc va !"}
        session["access_token"] = response["access_token"]
        session["refresh_token"] = response["refresh_token"]
        print("refresh" + str(nbr))
        return api_requests(url, nbr-1)
    
    # Return the response of the Spotify API
    return response

app.run(host="0.0.0.0", port=5000)