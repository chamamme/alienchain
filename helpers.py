import json
import logging
from _sha256 import sha256

LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s "
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger()


def log(message, level='info'):
    return logger.__getattribute__(level)(message)


def is_valid_nonce(block, test_hash):
    """
    Checks if nonce is valid
    :return:
    """
    block.nonce = block.nonce
    trial_hash = block.compute_hash()
    return trial_hash == test_hash


def compute_hash(object):
    """
    Generates a hash of a string
    :return:
    """
    tx_string = json.dumps(object.__dict__, sort_keys=True)

    return sha256(tx_string.encode()).hexdigest()
