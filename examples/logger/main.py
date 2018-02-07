from flask import Flask, abort, request
import json

app = Flask(__name__)

@app.route("/")
def hello():
    return "Logger running..."

@app.route('/in', methods=['POST']) 
def scale_in():
    print('Scale In Endpoint hit :')
    if not request.json:
        abort(400)
    return json.dumps(request.json)

@app.route('/out', methods=['POST']) 
def scale_out():
    print('Scale Out Endpoint hit :')
    if not request.json:
        abort(400)
    return json.dumps(request.json)