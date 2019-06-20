from PyCRC.CRC32 import CRC32
import struct
import serial
import time


class Message:
    def __init__(self, opcode, param1=0x12345678, param2=0x87654321, payload=""):
        self.payload = payload
        self.SYNC_WORD = 0xA5A5A5A5         # 32 bit
        self.opcode = opcode                # 32 bit
        self.param1 = param1                # 32 bit
        self.param2 = param2                # 32 bit
        self.payload_crc = None             # 32 bit
        self.payload_length = len(payload)  # 32 bit
        self.hdr_crc = None                 # 32 bit

    def update_payload(self, payload):
        self.payload_length = len(payload)  # 32 bit
        self.payload = payload
        self.hdr_crc = None                 # 32 bit

    def update_params(self, param1, param2=0):
        self.param1 = param1                # 32 bit
        self.param2 = param2                # 32 bit
        self.hdr_crc = None                 # 32 bit


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
        hdr_bin = struct.pack("I I I I I I",  self.SYNC_WORD,
                                              self.opcode,
                                              self.param1,
                                              self.param2,
                                              self.payload_length,
                                              self.payload_crc)
        hdr_crc = CRC32().calculate(hdr_bin)
        return hdr_bin + struct.pack("I", hdr_crc) + str.encode(self.payload)

    def log(self):
        print("Opecode:     ", self.opcode)
        print("param1:      ", self.param1)
        print("param2:      ", self.param2)
        print("payload len: ", self.payload_length)
        print("payload:     ", self.payload)


def uart_read(uart, msg):
    cnt = 0
    while (cnt < 4):
        b = uart.read(1)
        if b == b'':
            return False
        if b == b'\xa5':
            cnt += 1;
        else:
            print("--- Sync Error ---")
            cnt = 0
    hdr = uart.read(24)
    if hdr == b'':
        return False
    if msg.bin2hdr(b'\xa5'*4 + hdr):
        msg.bin2payload(uart.read(msg.payload_length))
    else:
        return False
    return True


def main():
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    ser.timeout = 1
    msg_m2s = Message(0x20, 0, 0) # opcode SEND
    msg_s2m = Message(0x20) # opcode SEND
    msg_ack = Message(0x10) # opcode SEND
    m_rx_cnt = 0
    m_tx_cnt = 1
    s_rx_cnt = 0
    s_tx_cnt = 0
    PRINT_CYCLE = 10
    print_cnt = PRINT_CYCLE
    while True:
        msg_m2s.update_payload("%8d%8d" % (m_rx_cnt, m_tx_cnt))
        m_tx_cnt += 1
        m = msg_m2s.msg2bin()

        if len(m) > 64:
            # send in two steps to  allow the ESP avoid fifo overflow while ESP calculate the CRC
            ser.write(m[:32])
            time.sleep(0.01)
            ser.write(m[32:])
        else:
            ser.write(m)
        # ser.write(msg_m2s.msg2bin())
        ret = uart_read(ser,msg_ack)
        if (not ret) or msg_ack.payload[:2] != b'OK':
            print("host <-> LoRa com error")
            msg_ack.log()
            continue
        ret = uart_read(ser,msg_s2m)
        if ret:
            m_rx_cnt+=1
            s_rx_cnt = int(msg_s2m.payload[0:8])
            s_tx_cnt = int(msg_s2m.payload[8:16])
        else:
            print("Timeout")
        print_cnt -= 1
        if not print_cnt:
            print_cnt = PRINT_CYCLE
            m_mer = 1 if s_tx_cnt == 0 else (1-float(m_rx_cnt/s_tx_cnt))
            s_mer = 1-float(s_rx_cnt/m_tx_cnt) # m_tx_cnt never == 0
            print("M MER: %f ; S MER: %f" % (m_mer , s_mer),
                  "MRx: ", m_rx_cnt, "MTx: ",  m_tx_cnt, "STx: ", s_rx_cnt)




if __name__ == '__main__':
    main()

