from hashlib import sha512
import json
import time



from flask import Flask, request
import requests


# A class that represents a Block, whcih stores one or more
# pieces of data, in the immutable Blockchain


class Block:
    # One or more piece of data(author, contetn of post and timestamp) will be stored in a block
    # The blocks containing the data are generated frequently and added to the blockchain. These block has unique ID.
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0


    # A function that creates the hash of the block content
    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha512(block_string.encode()).hexdigest()

# End of Block class


# A class that represents an immutable list of Block objects are chained together by hashes, a Blockchain.
class Blockchain:
    # Difficult of PoW algorithm
    difficulty = 2
    # One or more blocks will be stored and chained toghether on the Blockchain, starting by the genisi block
    def __init__(self):
        self.unconfirmed_transactions = [] # These are pieces of data that are not yet added to the Blockchain.
        self.chain = [] # The immutable list that represets the actual Blockchain
        self.create_genesis_block()

    # Generates genesis block and appends it to the Blockchain
    # The Block has index o, previous_hash of 0 and a valid hash
    def create_genesis_block(self):
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    # Verifed block can be added to the chain, add it and return True or False
    def add_block(self, block, proof):
        previous_hash = self.last_block.hash
        # Verify that the prvious_hash field of the block to be added points to the hash of the latest block
        # and tjhat the PoW that is provided is correct
        if (previous_hash !=block.previous_hash or not self.is_valid_proof(block, proof)):
            return False
        # Add new block to the chain after verification
        block.hash = proof
        self.chain.append(block)
        return True


    # Serve as interface to add the transactions to the blockchain by adding them
    # and then figuring out the PoW
    def mine(self):
        # if uncofirmed_transactions is empyt, no mining to be done
        if not self.unconfirmed_transactions:
            return False
        last_block = self.last_block
        # Creates a new block to be added to the chain
        new_block = Block(last_block.index + 1, \
                    self.unconfirmed_transactions, \
                    time.time(), \
                    last_block.hash)

        # Running PoW algorithm to obtain valid has and consensus
        proof = self.proof_of_work(new_block)
        # Verifed block can be added to the chain (Previosu hash matches and PoW is valid) then add it
        self.add_block(new_block, proof)
        # Empties the list of unconfirmed transactions since they are added to the chain
        self.unconfirmed_transactions = []
        # Announce to the network once a block has been mined, other blocks can simply verify the PoW and add it to the respective chains
        announce_new_block(new_block)
        # Returns the index of the blockthat was added to the chain
        return new_block.index



        # proof of work algorithm that tries different values of nonce in order to get a hash
        # that satistfies the difficulty criteria

    def proof_of_work(self, block):
        block.nonce = 0
        computed_hash = block.compute_hash()
        while not computed_hash.startswith("0" * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash


    # Adds a new transaction to the list of unconfirmed transactions(not yet in the blockchain)
    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

        # Checks if the chain is valid at the current time

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"
        for block in chain:
            block_hash = block.hash
            # Removes the hash attributes to recompute the hash again using compute_hash
            delattr(block, "hash")
            if not cls.is_valid_proof(block, block.hash) or previous_hash != block.previous_hash:
                result = False
                break
            block.hash = block_hash
            previous_hash = block_hash
        return result


            # Returns the current last Block in the Blockchain
    @classmethod
    def is_valid_proof(cls, block, block_hash):
        return (block_hash.startswith("0" * Blockchain.difficulty) and block_hash == block.compute_hash())

    @property
    def last_block(self):
        return self.chain[-1]
# End of Blockchain class



# Flask web application
# create Flask web application
app = Flask(__name__)
# The node's copy of the blockchain
blockchain = Blockchain()
# A set that stores the addresses to other participating members in the network
peers = set()

# Create a new endpoint and binds the function to the uRL
@app.route("/new_transaction", methods=["POST"])
# Submit a new transaction, which add new data to the blochain
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "content"]
    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404
    tx_data["timestamp"] = time.time()
    blockchain.add_new_transaction(tx_data)
    return "Success", 201


@app.route("/chain", methods=["GET"])
def get_chain():
    consensus()
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length" : len(chain_data), "chain" : chain_data})
        

# Create a new endpoint and bind the function to the URL
@app.route("/mine", methods=["GET"])
# Requests the node to mine the uncofirmed transaction (if any)
def mine_uncofirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "There are not transactions to mine"
    return "Block #{0} has been mined.".format(result)


# Cretes a new endpoint and binds the function to the URL
# Adds new peers to the network
def register_new_peers():
    nodes = request.get_json()
    if not nodes:
        return "Invalid data", 400
    for node in nodes:
        peers.add(node)
    return "Success", 201


# Create new endpoint and bind the function to the URL
@app.route("/pending_tx")
# Queries uncofirmed transactions

def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


# A simple algorithm to achieve consensus to mantain the intergrity of Blochain
# If a longer valid chain is found, the chain is replaced with it and returns True, otherwise nothing happens and returns false
def consensus():
    global blockchain
    longest_chain = None
    curr_len = len(blockchain.chain)
    # Achieve consensus by chacking th Json fields of every node in the network
    for node in peers:
        response = request.get("http://{0}".format(node))
        length = response.json()["length"]
        chain = response.json()["chain"]
        if length > curr_len and blockchain.check_chain_validity(chain):
            curr_len = length
            longest_chain = chain
    if longest_chain:
        blockchain = longest_chain
        return True
    return False


# Create a new endpoint and binds the function to the URl
@app.route("/add_block", methods=["POST"])
# Adds a block mined by user to the node's chain
def validate_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"], \
            block_data["transactions"], \
            block_data["timestamp", block_data["previous_hash"]])
    proof = block_data["hash"]
    added = blockchain.add_block(block, proof)
    if not added:
        return "The Block was discarded by the node.", 400
    return "The block was added to the chain.", 201


# Announce to the network once a block has been moned
def announce_new_block(block):
    for peer in peers:
        url = "http://{0}/add_block".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))

# Run the Flask web app
app.run(port=8000, debug=True)





