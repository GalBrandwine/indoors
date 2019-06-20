#!/usr/bin/env python
import serial
import time
import lora_api


def main():
    """ TTY IS HARDCODED MAKE SURE IT WORK SMARTER - SHMIDET HAS A SOLUTION FOR IT...."""
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    ser.timeout = 1

    # There 3 types of messages:
    # [0] msg_m2s - message for sending to slave
    # [1] msg_s2m - message for receiving data from slave
    # [2] msg_ack - message for receiving acknowledge from slave (its a python object that will be filled with data from slave's ack
    msg_m2s = lora_api.Message(0x20, 0, 0)  # opcode SEND
    msg_s2m = lora_api.Message(0x20)  # opcode SEND
    msg_ack = lora_api.Message(0x10)  # opcode SEND

    # Counters for debugging communication protocol.
    m_rx_cnt = 0
    m_tx_cnt = 1
    s_rx_cnt = 0
    s_tx_cnt = 0

    PRINT_CYCLE = 10
    print_cnt = PRINT_CYCLE

    # An example for usage of the master slave communication.
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
            ser.write(b'm')
            print (m)
        # ser.write(msg_m2s.msg2bin())
        ret = lora_api.uart_read(ser, msg_ack)
        print ("test: {}".format(msg_ack.payload[:2]))
        if (not ret) or msg_ack.payload[:2] != b'OK':

            print("host <-> LoRa com error")
            msg_ack.log()
            continue
        ret = lora_api.uart_read(ser, msg_s2m)
        if ret:
            m_rx_cnt += 1
            s_rx_cnt = int(msg_s2m.payload[0:8])
            s_tx_cnt = int(msg_s2m.payload[8:16])
        else:
            print("Timeout")
        print_cnt -= 1
        if not print_cnt:
            print_cnt = PRINT_CYCLE
            m_mer = 1 if s_tx_cnt == 0 else (1 - float(m_rx_cnt / s_tx_cnt))
            s_mer = 1 - float(s_rx_cnt / m_tx_cnt)  # m_tx_cnt never == 0
            print("M MER: %f ; S MER: %f" % (m_mer, s_mer),
                  "MRx: ", m_rx_cnt, "MTx: ", m_tx_cnt, "STx: ", s_rx_cnt)


if __name__ == '__main__':
    main()
