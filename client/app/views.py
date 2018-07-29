import datetime
import json

import requests
from flask import render_template, redirect, request

from client.app import app

# The node with which our application interacts, there can be multiple
# such nodes as well.
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

posts = []


def fetch_posts():
    """
    Function to fetch the chain from a blockchain node, parse the
    data and store it locally.
    """
    get_chain_address = "{}/chain".format(CONNECTED_NODE_ADDRESS)
    pending_address = "{}/pending_tx".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        content = []
        blks = []
        chain = json.loads(response.content)
        for block in chain["chain"]:
            blks.append(block)
            for tx in block["transactions"]:
                tx["index"] = block["index"]
                tx["hash"] = block["previous_hash"]
                content.append(tx)

        global posts, blocks
        posts = sorted(content, key=lambda k: k['timestamp'],
                       reverse=True)
        blocks = blks


@app.route('/')
def index():
    fetch_posts()

    return render_template('index.html',
                           title='AlienChain Posts',
                           posts=posts,
                           blocks=blocks,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string)

@app.route('/tasks')
def tasks():
    fetch_posts()

    return render_template('courier.html',
                           title='AlienChain Posts',
                           posts=posts,
                           blocks=blocks,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string)


@app.route('/tasks/pickup')
def pickup():
   tasks_id = request.args.task_id




@app.route('/submit', methods=['POST'])
def submit_textarea():
    """
    Endpoint to create a new transaction via our application.
    """
    user = request.form["owner"]
    title = request.form["title"]
    location_from = request.form["from"]
    location_to = request.form["to"]
    description = request.form["description"]

    data = {
        'user': user,
        'title': title,
        'from': location_from,
        'to': location_to,
        'description': description,
    }

    post_object = {
        'data': data,
        'type': "request",
        'owner': user
    }

    # Submit a transaction
    new_tx_address = "{}/transaction".format(CONNECTED_NODE_ADDRESS)

    requests.post(new_tx_address,
                  json=post_object,
                  headers={'Content-type': 'application/json'})

    return redirect('/')


def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')
