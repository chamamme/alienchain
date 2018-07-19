import json
import time
from _sha256 import sha256


class Transaction:

    def __init__(self, data, signer, tag=None):
        """
        :param data:
        :param signer: the public key of the sender
        """
        self.data = data
        self.signer = sha256(signer.encode()).hexdigest()
        self.timestamp = time.time()
        self.hash = self.compute_hash()
        self.tag = tag

    def compute_hash(self):
        """
        Generates a hash of the transaction
        :return:
        """
        tx_string = json.dumps(self.__dict__, sort_keys=True)

        return sha256(tx_string.encode()).hexdigest()
