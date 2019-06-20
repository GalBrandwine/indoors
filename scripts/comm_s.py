#!/usr/bin/env python
import serial
import lora_api

PRINT_CYCLE = 10


def main():
    ser = serial.Serial('/dev/ttyUSB1', 115200)
    rx_msg = lora_api.Message(0x20)  # opcode SEND
    tx_msg = lora_api.Message(0x20, 0, 0)  # opcode SEND
    ack_msg = lora_api.Message(0x10)  # opcode SEND
    s_rx_cnt = 0
    s_tx_cnt = 0
    print_cnt = PRINT_CYCLE
    while True:
        lora_api.uart_read(ser, rx_msg)  # no timeout
        s_rx_cnt += 1
        s_tx_cnt += 1
        rx_msg.log()
        tx_msg.update_payload("%8d%8d" % (s_rx_cnt, s_rx_cnt) + " " * 200)
        ser.write(tx_msg.msg2bin())
        ret = lora_api.uart_read(ser, ack_msg)  # no timeout
        if not ret:
            print("Error ...")
            return
        print_cnt -= 1
        if not print_cnt:
            print_cnt = PRINT_CYCLE
            print("Rx/Tx Couter: %d" % s_rx_cnt)


if __name__ == '__main__':
    main()
