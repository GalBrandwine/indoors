import logging
import struct

from PyCRC.CRC32 import CRC32


class Message:
    def __init__(self, opcode, param1=0, param2=0, payload=""):
        self.payload = payload
        self.SYNC_WORD = 0xA5A5A5A5  # 32 bit
        self.opcode = opcode  # 32 bit
        self.param1 = param1  # 32 bit
        self.param2 = param2  # 32 bit
        self.payload_crc = None  # 32 bit
        self.payload_length = len(payload)  # 32 bit
        self.hdr_crc = None  # 32 bit
        self.logger = logging.getLogger('lora_api_logger')

    def update_payload(self, payload):
        self.payload_length = len(payload)  # 32 bit
        self.payload = payload
        self.hdr_crc = None  # 32 bit

    def update_params(self, param1, param2=0):
        self.param1 = param1  # 32 bit
        self.param2 = param2  # 32 bit
        self.hdr_crc = None  # 32 bit

    def bin2hdr(self, bin_msg):
        (self.SYNC_WORD, self.opcode, self.param1,
         self.param2, self.payload_length,
         self.payload_crc, self.hdr_crc) = struct.unpack("I I I I I I I", bin_msg[:28])

        hdr_crc = CRC32().calculate(bin_msg[:24])

        if hdr_crc != self.hdr_crc:
            print("Header CRC error %08X %08X" % (self.hdr_crc, hdr_crc))
            return False
        return True

    def bin2payload(self, bin_payload):
        self.payload = bin_payload
        payload_crc = CRC32().calculate(self.payload)
        if payload_crc != self.payload_crc:
            print("Payload CRC error %08X %08X" % (self.payload_crc, payload_crc))
            return False
        return True

    def msg2bin(self):
        self.payload_crc = CRC32().calculate(self.payload)
        hdr_bin = struct.pack("I I I I I I", self.SYNC_WORD,
                              self.opcode,
                              self.param1,
                              self.param2,
                              self.payload_length,
                              self.payload_crc)
        hdr_crc = CRC32().calculate(hdr_bin)
        ret = hdr_bin + struct.pack("I", hdr_crc)
        if self.payload_length:
            ret += str.encode(str(self.payload))
        return ret

    def log(self):
        self.logger.info("Opecode:     {}\n" +
                         "param1:      {}\n" +
                         "param2:      {}\n" +
                         "payload len: {}\n" +
                         "payload:     {}\n".format(
                             self.opcode, self.param1, self.param2, self.payload_length, self.payload
                         )
                         )


def uart_read(uart, msg):
    cnt = 0
    ret = True
    bak_timeout = uart.timeout
    while (cnt < 4):
        b = uart.read(1)
        if b == '\xa5':
            cnt += 1
        else:
            print("--- Sync Error: uart flushed ---")
            uart.flush()
            return False
            cnt = 0
    uart.timeout = 1
    hdr = uart.read(24)
    if len(hdr) == 0:
        print("Header timeout")
        ret = False
    else:
        if msg.bin2hdr(b'\xa5' * 4 + hdr):
            payload = uart.read(msg.payload_length)
            if len(payload) == 0:
                ret = False
                print("Payload timeout")
            else:
                if msg.bin2payload(payload) == False:
                    ret = False
        else:
            ret = False
    uart.timeout = bak_timeout
    return ret
