"""Legacy call signature adapter for the official ftservo-python-sdk 2.x."""
from scservo_sdk import PortHandler, sms_sts

class PacketHandler:
    def __init__(self, protocol):
        if protocol != 0:
            raise ValueError('Only STS protocol supported')
        self.handlers = {}

    def __getattr__(self, name):
        def call(port, *args):
            if id(port) not in self.handlers:
                self.handlers[id(port)] = sms_sts(port)
            handler = self.handlers[id(port)]
            return getattr(handler, name)(*args)
        return call
