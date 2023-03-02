# Creating a Cryptocurrency

# Need to install
# Flask : pip install Flask==0.12.2
# Postman HTTP Client: https://www.getpostman.com/
# requests==2.18.4: pip install requests==2.18.4


# Importing the Libraries
# datetime for current timestamp
# hashlib for hashing the blocks
# json for encode blocks before hashing
# Flask class for the web app
# jsonify to making requests for the blockchain
# The Request, in Flask, is an object that contains all the data sent from the Client to Server. Here for connecting nodes

import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse


# 1) Building our BlockChain

# Best practise to start with a Class
class Blockchain:

    def __init__(self):
        self.chain = []
        # build a mempool
        self.transactions = []
        self.create_block(proof=1, previous_hash='0')
        # different people
        self.nodes = set()

    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions}
        # after transations are put onto block, then empty the mempool
        self.transactions = []
        # after each created block append it to the chain
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        # proof is Nonce
        # new and previous proof square subtracted for maintaining asyymetric and complex
        new_proof = 1
        check_proof = False
        # say str(5) = '5', .encode() => b'5', hexdigest() => 64 char hexa hash
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:5] == '00000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def get_hash(self, block):
        # json.dumps to convert dictionary to strings
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        # 1)Check if prev hash of the block is equal to the hash of the previous block
        # 2)Check if the proof is correctly providing hash with '0000' (here)
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.get_hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:5] != '00000':
                return False
            previous_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender': sender,
                                  'receiver': receiver,
                                  'amount': amount})
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1

    def add_node(self, address):
        # address = 'http://127.0.0.1:5000/'
        # parsed_url = urlparse(address)
        # parsed_url : ParseResult(scheme='http', netloc='127.0.0.1:5000', path='/', params='', query='', fragment='')
        parsed_url = urlparse(address)
        # parsed_url.netloc : '127.0.0.1:5000'
        # set doesnt have append, it has add instead
        self.nodes.add(parsed_url.netloc)

    # for each node check with the chain of all other nodes
    # find the largest chain and make the current nodes's chain as that longest chain.
    # this function works with each node seperately
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False


# 2) Mining our BlockChain

# Creating Web App

app = Flask(__name__)

# Creating an address for the node on Port 5000

node_address = str(uuid4()).replace('-', '')

# Creating a BlockChain Instance

blockchain = Blockchain()


# Mining a new block

@app.route('/mine_block', methods=['GET'])
def mine_block():
    # Get previous block, its proof (Noence), its hash and thus new block's proof and create_block
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.get_hash(previous_block)
    blockchain.add_transaction(sender=node_address, receiver='Riteesh', amount=1)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message': 'Congrats, you mined a block !',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'transactions': block['transactions']}
    # convert response in json format so jsonify
    return jsonify(response), 200


# Getting the whole BlockChain

@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200


# Checking if the Blockchain is valid

@app.route('/is_valid', methods=['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid == True:
        response = {'message': 'The BlockChain is VALID'}
    else:
        response = {'message': 'The BlockChain is INVALID'}
    return jsonify(response), 200


# Adding a new transaction to the Blockchain

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    # inside contet of postman body
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all(key in json for key in transaction_keys):
        return 'Some elements of the transaction are missing', 400
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'message': f'This transaction will be added to Block {index}'}
    return jsonify(response), 201


# 3) Decentralising our BlockChain

# Connecting new nodes

@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No Node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All the nodes are now connected. The Ritecoin BLockchain has the following nodes : ',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201


# Replacing the chain by the longest chain if needed

@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'The nodes had different chains so the chains were replaced by the longest chain',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'The chain itself is the largest one.',
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200


# Running the app

app.run(host='0.0.0.0', port=5000)
