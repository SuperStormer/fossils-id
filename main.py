from flask import Flask
from threading import Thread
import subprocess
app = Flask('')

@app.route('/')
def main():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=2000)

def keep_alive():
    server = Thread(target=run)
    server.start()

if __name__ == '__main__':
    keep_alive()
    subprocess.Popen(["./redis-stable/src/redis-server", "--port", "3001"])
    subprocess.run(["python", "./main_orig.py"])