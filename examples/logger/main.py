from flask import Flask, abort, request
import logging
import json

app = Flask(__name__)
app.debug = True

@app.route("/")
def hello():
    return "Logger running..."

@app.route('/in', methods=['POST']) 
def scale_in():
    app.logger.info('Scale In Endpoint hit')
    if not request.json:
        abort(400)
    app.logger.debug(json.dumps(request.json))
    return json.dumps(request.json)

@app.route('/out', methods=['POST']) 
def scale_out():
    app.logger.info('Scale Out Endpoint hit')
    if not request.json:
        abort(400)
    app.logger.debug(json.dumps(request.json))
    return json.dumps(request.json)