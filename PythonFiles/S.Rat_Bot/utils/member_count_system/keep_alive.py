from flask import abort, request
from dotenv import load_dotenv
import os
from threading import Thread
import status_state
from shared import app 

load_dotenv()
STATUS_TOKEN = os.getenv("STATUS_TOKEN")

@app.route('/')
def index():
    return "✅ S-RatBot is running.", 200

@app.route('/status')
def status():
    if status_state.status_up:
        return "✅ Bot is healthy.", 200
    else:
        return "❌ Bot is having issues or down for maintenance.", 503

SECRET = STATUS_TOKEN

@app.route('/set_down')
def set_down():
    if request.args.get('token') != SECRET:
        abort(403)
    status_state.status_up = False
    return "Status set to DOWN", 200

@app.route('/set_up')
def set_up():
    status_state.status_up = True
    return "Status set to UP", 200

def run():
    import internalroute  # delayed import
    app.run(host='0.0.0.0', port=5000)

print(app.url_map)

def keep_alive():
    t = Thread(target=run)
    t.start()
