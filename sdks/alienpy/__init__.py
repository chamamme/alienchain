import json,requests
from _blake2 import blake2b


NODE_ADDRESS = "http://localhost:8000"


class crypto:

    def __init__(self):
        self.node = NODE_ADDRESS
        pass

    @classmethod
    def getHash(cls, string):
        """
        Function to generate a hash of a string using Black2b Algo
        I chose Black2b due it its speed and security level
        :param string:
        :return:
        """
        hash = blake2b(string.encode()).hexdigest()
        cls.signature = hash
        return cls.signature

    @property
    def signer(self):
        return self.signer


class Transaction:
    __types = ['create', 'update']  # transaction types

    endpoint = "{}/transaction".format(NODE_ADDRESS)

    def __init__(self):
        self.__signature = None
        self.__owner = None
        self.__data = None
        self.__group = None
        self.__tx_type = None
        self.__types = None
        pass

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, data):
        if not json.loads(data):
            raise TypeError("Data must be of type json")
        print(data)
        self.__data = data

    @property
    def owner(self):
        return self.__owner

    @owner.setter
    def owner(self, owner):
        self.sign(owner)
        self.__owner = owner

    @property
    def group(self):
        return self.__group

    @group.setter
    def group(self, group_name):
        self.__group = group_name

    @property
    def tx_type(self):
        return

    @tx_type.setter
    def tx_type(self, type):
        """
        Function to set the type of trasaction
        ['create','update']
        :param type:
        :return:
        """
        if not type(type) == 'string':
            raise TypeError("Type must be a string")
        self.__tx_type = type

    @property
    def signature(self):
        return self.__signature

    @signature.setter
    def signature(self, signature):
        self.__signature = signature

    def sign(self, string):
        """
        Function to generate a hash hex_diagest from a string
        :param string:
        :return:
        """
        self.__signature = crypto.getHash(string)

    def create(self):
        """
        Function to create a new transaction
        :return:
        """
        if not self.__data:
            raise ValueError("data is required")
        if not self.__group:
            raise ValueError("group is required")
        if not self.__signature:
            raise ValueError("signature  is required")
        payload = {
            'data': self.__data,
            'owner': self.__signature,
            'group': self.__group
        }
        req = requests.post(self.endpoint, json=payload, headers={'Content-type': 'application/json'})
        return req.text

    def get(self, tx_hash):
        # Get the transaction
        endpoint = "{}/{}".format(self.endpoint, tx_hash)
        req = requests.get(endpoint)
        return req.text

    def update(self, object_id, data=None, owner=None, ):
        """
        Function to update an already existing transaction
        :param object_id:
        :return:
        """
        # Get the transaction
        if data:
            self.__data = data
        if owner:
            self.__owner = owner
        if not self.__owner or self.__data:
            raise ValueError('Owner and data required')
        data = json.loads(self.get(object_id))
        signer = crypto.getHash(self.__owner)
        tx_signer = data.get('signer')
        if not signer == tx_signer:
            raise BaseException("You dont have the privilege to amend")
        # LETS UPDATE IT
        obj_id = data['object_id']
        data = self.__data
        # print("@herer{}".format(self.__data))
        payload = json.dumps({
            'object_id': obj_id,
            'data': data
        })

        req = requests.put(self.endpoint, data=payload, headers={'Content-type': 'application/json'})

        return req.text


class Block():
    @classmethod
    def get(cls, block_hash=None, block_index=None):
        """
        Function to get a blocks or a single block
        :param block_hash:
        :param block_index:
        :return:
        """
        # Get the block info
        id = block_index if block_index else block_hash
        if(id):
            endpoint = "{}/blocks/{}".format(NODE_ADDRESS, id)
        else:
            endpoint = "{}/blocks".format(NODE_ADDRESS)
        req = requests.get(endpoint)
        payload = {'status':req.status_code,"data":req.text}

        return payload


# tx = Transaction()

# tx.owner = "Andrew Chamamme"
# tx.data = '{"asdfasdf":"asdasd"}'
# tx.group = 'asdde'
# # rs = tx.update('1532968669.3950505')
# tx.create()
#
# print(tx.__dict__)

class aliensql():

    @classmethod
    def get(self):
        pass


if __name__ == "__main__":
    blocks = Block.get()
    print(blocks)

