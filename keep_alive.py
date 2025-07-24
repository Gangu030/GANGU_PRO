# keep_alive.py
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "GANGU PRO is live!"

def run():
    # Using host='0.0.0.0' and port=8080 is standard for Replit web servers
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()