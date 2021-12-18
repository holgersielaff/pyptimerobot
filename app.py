from flask import Flask

app = Flask(__name__)


@app.route('/')
def index():
    return 'This may be a Web UI for the uptimerobot in the future'


if __name__ == '__main__':
    app.run()
