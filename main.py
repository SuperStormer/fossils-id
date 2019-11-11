import os
import subprocess
from threading import Thread

from flask import Flask

app = Flask('')

@app.route('/')
def main():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=os.getenv("PORT") or 2000)

def keep_alive():
    server = Thread(target=run)
    server.start()

if __name__ == '__main__':
    keep_alive()
    subprocess.Popen(["redis-server", "--port", "3001"])
    subprocess.run(["python", "./bot.py"])
