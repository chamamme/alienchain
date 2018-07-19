import logging

LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s "
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger()


def log(message, level='info'):
    return logger.__getattribute__(level)(message)
