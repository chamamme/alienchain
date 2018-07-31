from _thread import start_new_thread
from hashlib import  blake2b
import json
import time

import pymongo as pymongo
from flask import Flask, request, Response
import requests

from server.transaction import Transaction
from helpers import log, is_valid_nonce


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0

    def compute_hash(self):
        """
        A function that returns the hash of the block contents.
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return blake2b(block_string.encode()).hexdigest()


class Blockchain:
    # difficulty of our PoW algorithm. ie the number of preceding zeros
    difficulty = 2
    mongoClient = None
    db = None

    def __init__(self):
        log("Initializing Blockchain", "info")
        self.startDatabase()
        self.unconfirmed_transactions = []
        self.chain = []
        self.loadBlocks()
        # self.create_genesis_block()

    def startDatabase(self):
        try:
            client = pymongo.MongoClient("localhost", 27017)
            self.db = client.alien_database
            log("AlienChain database started")
        except Exception as e:
            log("Failed to start database. {}".format(e), 'warning')

    def loadBlocks(self):
        try:
            if self.db.blockchain.count() > 0:
                for block in self.db.blockchain.find({}, {'_id': 0}):
                    # block = json.loads(str(block))
                    block_obj = Block(block['index'], block['transactions'], block['timestamp'], block['previous_hash'])
                    block_obj.hash = block['hash']
                    block_obj.nonce = block['nonce']
                    self.chain.append(block_obj)
                # check the chains validity
                if not self.check_chain_validity(self.chain):
                    raise ValueError("Invalid chain")
            else:
                self.create_genesis_block()
        except Exception as e:
            log("Failed to load blockchain data: {}".format(e), 'critical')

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], time.time(), "0")
        # genesis_block.hash = genesis_block.compute_hash()
        # self.chain.append(genesis_block)
        proof = self.proof_of_work(genesis_block)
        self.add_block(genesis_block, proof)
        log("Genesis block created: {}".format(json.dumps(genesis_block.__dict__)))

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        if block.index != 0:
            previous_hash = self.last_block.hash
        else:
            previous_hash = block.previous_hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        # insert into db
        try:
            block_json = json.dumps(block.__dict__)
            collection = self.db.blockchain
            id = collection.insert_one(json.loads(block_json)).inserted_id
            if id:
                log("DB INSERT SUCCESSFUL")
        except Exception as e:
            log("Failed to insert into db: {}".format(e), "warning")
        if not id:
            log("failed to insert into db")
        log("Block #{} created {} ".format(block.index, block_json))
        return True

    def proof_of_work(self, block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_transaction(self, transaction):
        try:
            self.unconfirmed_transactions.append(transaction)
            return transaction
            log("Transaction received")
        except:
            log("Transaction failed")

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []
        # announce it to the network
        announce_new_block(new_block)

        return new_block.index

    def miner(self):
        """
        A function to mine infinitely
        :param self:
        :return:
        """
        try:
            while True:
                self.mine()
        except:
            return False


app = Flask(__name__)

# the node's copy of blockchain
blockchain = Blockchain()

# generate genesis block
# blockchain.create_genesis_block()
# start a mining thread
start_new_thread(blockchain.miner, ())

# the address to other participating members of the network
peers = set()

@app.route('/transaction/<tx_hash>', methods=['GET'])
def getTransaction(tx_hash):
    search_key = {'transactions.hash': tx_hash}
    block = blockchain.db.blockchain.find_one(search_key, {"_id": 0})
    # print(list(prev_tx))
    if block is not None:
        for tx in block['transactions']:
            if tx['hash'] == tx_hash:
                tx['block_index'] = block['index']
                tx['block_hash'] = block['hash']
                tx['block_time'] = block['timestamp']
                ress = json.dumps(tx)
                return Response(ress, status=200, mimetype='application/json')
    return Response("No match found", status=404, mimetype='application/json')

# endpoint to submit a new transaction
@app.route('/transaction', methods=['POST'])
def newTransaction():
    """
    # endpoint to submit a new transaction
    :return:
    """
    tx_data = request.get_json()
    required_fields = ["data", "owner", "group"]

    for field in required_fields:
        if not tx_data.get(field):
            log("Invalid transaction")
            return "Invalid transaction data", 400

    tx = Transaction(
        data=tx_data['data'],
        owner=tx_data['owner'],
        group=tx_data['group']
    )
    new_tx = blockchain.add_new_transaction(tx.__dict__)
    resp = json.dumps(new_tx)
    return Response(resp, status=200, mimetype="application/json")


# endpoint to update a  transaction/object
# object_id and data is required
@app.route('/transaction', methods=['PUT'])
def updateTransaction():
    """
    # endpoint to update a  transaction/object
    # object_id and data is required
    :return:
    """
    form_data = request.get_json()
    log(form_data)
    required_fields = ["object_id", "data"]

    for field in required_fields:
        if not form_data.get(field):
            msg = "Invalid transaction: object_id,data fields are required"
            log(msg)
            return msg, 400
    # fetch tx with object_id
    search_key = {'transactions.object_id': form_data['object_id']}
    blocks = blockchain.db.blockchain.find(search_key, {"_id": 0, "transactions": 1}) \
        .sort([{"transactions.timestamp", -1}]) \
        .limit(1)

    # print(list(prev_tx))
    if blocks.count() > 0:
        block = list(blocks)[0]  # get the first block
        for tx in block['transactions']:
            if tx['object_id'] == form_data['object_id']:
                # print(tx)
                # print(tx['signer'])
                # print(tx['group'])
                new_tx = Transaction(
                    data=form_data['data'],
                    owner=tx['signer'],
                    group=tx['group']
                )
                new_tx.object_id = tx['object_id']
                new_tx = blockchain.add_new_transaction(new_tx.__dict__)
                ress = json.dumps(new_tx)
    return Response(ress, status=200, mimetype='application/json')


@app.route('/transaction/<float:object_id>', methods=['GET'])
def getTransactionByObjectId(object_id):
    search_key = {'transactions.object_id': object_id}
    blocks = blockchain.db.blockchain.find(search_key, {"_id": 0})
    block = list(blocks)[-1] if blocks.count() > 0 else []  #get the last/recent block
    txs = []
    if block :
        for tx in block['transactions']:
            if tx['object_id'] == object_id:
                tx['block_index'] = block['index']
                tx['block_hash'] = block['hash']
                tx['block_time'] = block['timestamp']
                txs.append(tx)
        ress = json.dumps(txs[-1]) if len(txs) > 0 else [] #get the last transaction with object_id = object_id
        return Response(ress, status=200, mimetype='application/json')
    return Response("No match found", status=404, mimetype='application/json')

# endpoint to return the node's copy of the chain.
@app.route('/blocks', methods=['GET'])
def getBlocks():
    # make sure we've the longest chain
    consensus()
    blocks = blockchain.db.blockchain.find({},{'_id':0})

    chain = list(blocks)
    chain_data = list(reversed(chain))
    result = json.dumps({"length": blocks.count(), "blocks": chain_data})
    return Response(result, mimetype='application/json')
# endpoint to return the node's copy of the chain.
@app.route('/blocks/<string:hash>', methods=['GET'])
def getBlock(hash):
    # make sure we've the longest chain
    consensus()
    block = blockchain.db.blockchain.find_one({"hash":hash},{'_id':0})
    result = json.dumps(block)
    return Response(result, mimetype='application/json')

# endpoint to return Block using it index.
@app.route('/blocks/<int:index>', methods=['GET'])
def getBlockByIndex(index):
    # make sure we've the longest chain
    consensus()
    block = blockchain.db.blockchain.find_one({"index":index},{'_id':0})
    result = json.dumps(block)
    return Response(result, mimetype='application/json')

# endpoint to return the node's copy of the chain.
@app.route('/chain', methods=['GET'])
def get_chain():
    # make sure we've the longest chain
    consensus()
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    result = json.dumps({"length": len(chain_data), "chain": chain_data})
    return Response(result, mimetype='application/json')


# endpoint to request the node to mine the unconfirmed
# transactions (if any). We'll be using it to initiate
# a command to mine from our application itself.
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    return "Block #{} is mined.".format(result)


# endpoint to add new peers to the network.
@app.route('/add_nodes', methods=['POST'])
def register_new_peers():
    nodes = request.get_json()
    if not nodes:
        return "Invalid data", 400
    for node in nodes:
        peers.add(node)

    return "Success", 201


@app.route('/peers', methods=['GET'])
def connected_peers():
    nodes = peers
    return json.dumps(list(nodes))


# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def validate_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp",
                             block_data["previous_hash"]])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


def consensus():
    """
    Our simple consnsus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('http://{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "http://{}/add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))


app.run(debug=True, port=8000)
