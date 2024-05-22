import array
import datetime
import math
import multiprocessing
import os
import sys
import threading
import time

from pySerialTransfer import pySerialTransfer as txfer
from pySerialTransfer.pySerialTransfer import MAX_PACKET_SIZE, Status

#baud_rate = 500000
baud_rate = 2000000
ports = [("COM3", "module_1")]

HAS_ACC_SAMPLES = True
HAS_STS_SAMPLES = True

NUM_ACC_SAMPLES = 1016
NUM_STS_SAMPLES = 512
DIAGNOSTIC_LEN = 108
DGC_LEN = 1
CFO_LEN = 4
TEMPERATURE_LEN = 4
VOLTAGE_LEN = 4
RX_DATA_LEN = 8
ACC_DATA_LEN = NUM_ACC_SAMPLES * 6 + 1
STS_DATA_LEN = NUM_STS_SAMPLES * 6 + 1

packets_per_frame = math.ceil(float(DIAGNOSTIC_LEN + DGC_LEN + CFO_LEN + TEMPERATURE_LEN + VOLTAGE_LEN + RX_DATA_LEN) / MAX_PACKET_SIZE)

if HAS_ACC_SAMPLES:        
    packets_per_frame += math.ceil(float(ACC_DATA_LEN) / MAX_PACKET_SIZE)

if HAS_STS_SAMPLES:        
    packets_per_frame +=  math.ceil(float(STS_DATA_LEN) / MAX_PACKET_SIZE)
    




MAGIC_BYTES = b'\x09\x09\x07\x05\x09\x01\x01\x05' * 3
MAGIC_BYTES_2 = b'\x05\x01\x01\x09\x05\x07\x09\x09'


def verify_checksum(data, received_checksum):
    calculated_checksum = sum(data) & 0xFFFF  # 16비트로 제한
    return ~calculated_checksum & 0xFFFF == received_checksum

def process_frame(frame_data, file, is_flush = False):    
    file.write(frame_data)  # 파일에 데이터 쓰기
    if is_flush:
        file.flush()
    pass

def read_from_serial(stop_event, port, baud_rate, module_name):    
    link = txfer.SerialTransfer(port, baud_rate)
    link.open()
    
    rx_cnt = 0   
    
    cur_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")   
    dir_name = f"output/{module_name}_{cur_time}"     
    os.mkdir(dir_name)

    while not stop_event.is_set():
        data = bytearray()
        if link.available() > 0:    
            data = bytearray(link.rx_buff[:link.bytes_read])
            magic_bytes_index = data.find(MAGIC_BYTES)
            rx_cnt += 1

            if magic_bytes_index != -1:
                is_error = False                                
                rx_frames = 0
                err_frames = 0
                rx_packets = 0
                frame_data = bytearray() 
                while not stop_event.is_set():                                    
                    with open(f"{dir_name}/{rx_cnt}", "ab") as file:               
                        if link.available() > 0:      
                            data = bytearray(link.rx_buff[:link.bytes_read]) 
                            if data.find(MAGIC_BYTES) != -1:                             
                                rx_frames = 0
                                err_frames = 0
                                rx_packets = 0
                                rx_cnt += 1
                                is_error = False
                                continue

                            frame_data += data
                            rx_packets += 1
                                        

                        elif link.status.value <= 0:
                            is_error = True

                            if link.status == Status.CRC_ERROR:
                                print('ERROR: CRC_ERROR')
                            elif link.status == Status.PAYLOAD_ERROR:
                                print('ERROR: PAYLOAD_ERROR')
                            elif link.status == Status.STOP_BYTE_ERROR:
                                print('ERROR: STOP_BYTE_ERROR')
                            else:
                                print('ERROR: {}'.format(link.status.name))  
                            
                            print(f"[{module_name}] rx_number: {rx_cnt}, frame number: {rx_frames}")

                            rx_packets += 1                        

                        if rx_packets == packets_per_frame:
                            if not is_error:
                                process_frame(frame_data, file)                                    
                                rx_frames += 1    
                            else:
                                err_frames += 1     

                            rx_packets = 0      
                            frame_data.clear()    
                            is_error = False  
                                       

                            if (rx_frames + err_frames) % 3600 == 0:
                                print(f'{module_name}_rx_frames: {rx_frames}')
                                print(f'{module_name}_err_frames: {err_frames}')
                    
    link.close()



if __name__ == "__main__":
    stop_event = multiprocessing.Event()
    jobs = []
    for port, name in ports:
        p = multiprocessing.Process(target=read_from_serial, args=(stop_event, port, baud_rate, name, ))
        p.start()
        jobs.append(p)

    try:
        while True:
            pass

    except KeyboardInterrupt:
        print('Program terminated by user.')
        stop_event.set()
    finally:
        for j in jobs:
            j.join()