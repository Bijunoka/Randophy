from flask import Flask, session, redirect, request, send_from_directory

from flask_session import Session
from redis import Redis
from urllib.parse import urlencode
import base64
from requests import post, get
import os

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
    "scope" : "playlist-modify-private user-read-currently-playing",
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

    session["access_token"] = r["access_token"]
    session["refresh_token"] = r["refresh_token"]
    
    return redirect("/")

@app.route('/', defaults={'filename': 'index.html'})
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

app.run(host="0.0.0.0", port=5000)