# web server to ensure our bot on repl is running continuosly
from flask import Flask
from threading import Thread
app = Flask(__name__)


@app.route("/")
def home():
    return "Hello World!"


def run():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
