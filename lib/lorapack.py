import os
import socket
import time
import struct
from network import LoRa
import pycom
import uos
import ubinascii


class LoraPack:

    _LORA_PKG_FORMAT = "!BBIBB"
    _LORA_PKG_ACK_FORMAT = "!BBB"

    def __init__(self, region):

        self.lora = LoRa(mode=LoRa.LORA, region=LoRa.US915)
        self.lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
        self.lora_sock.setblocking(False)
        self.device_id = self._get_device_id()

    def _get_device_id(self):
        id = ubinascii.hexlify(self.lora.mac()).upper().decode('utf-8')
        id = id[14:16]
        return int(id, 16)

    def _pack_message(self, id_destination: int, msg: int):
        return struct.pack(self._LORA_PKG_FORMAT,
                           self.device_id,
                           id_destination,
                           msg,
                           0,               # location
                           0,)              # Px
