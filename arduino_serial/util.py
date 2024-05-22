import struct
import math
import numpy as np

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

FREQ_OFFSET_MULTIPLIER = (998.4e6 / 2.0 / 1024.0 / 131072.0)
DW_TIME_UNIT = 1.0/499.2e6/128.0

DIAG_STRING_FORMAT = (
        '5B'   # ipatovRxTime[5]
        'B'    # ipatovRxStatus
        'H'    # ipatovPOA
        '5B'   # stsRxTime[5]
        'H'    # stsRxStatus
        'H'    # stsPOA
        '5B'   # sts2RxTime[5]
        'H'    # sts2RxStatus
        'H'    # sts2POA
        '6B'   # tdoa[6]
        'h'    # pdoa
        'h'    # xtalOffset
        'I'    # ciaDiag1
        'I'    # ipatovPeak
        'I'    # ipatovPower
        'I'    # ipatovF1
        'I'    # ipatovF2
        'I'    # ipatovF3
        'H'    # ipatovFpIndex
        'H'    # ipatovAccumCount
        'I'    # stsPeak
        'H'    # stsPower
        'I'    # stsF1
        'I'    # stsF2
        'I'    # stsF3
        'H'    # stsFpIndex
        'H'    # stsAccumCount
        'I'    # sts2Peak
        'H'    # sts2Power
        'I'    # sts2F1
        'I'    # sts2F2
        'I'    # sts2F3
        'H'    # sts2FpIndex
        'H'    # sts2AccumCount
)

def read_record_file(dir_name, file_index, has_acc_samples=False, has_sts_samples=False):
    packet_len = DIAGNOSTIC_LEN + DGC_LEN + CFO_LEN + TEMPERATURE_LEN + VOLTAGE_LEN + RX_DATA_LEN
    if has_acc_samples:
        packet_len += ACC_DATA_LEN
    if has_sts_samples:
        packet_len += STS_DATA_LEN   
        
    received_packet_dicts = []
    
    with open(f"output/{dir_name}/{file_index}", 'rb') as f:    
        while True:
            packet_bytes = f.read(packet_len)
            
            if not packet_bytes:
                break
            
            received_packet_dicts.append(parse_packet(packet_bytes, has_acc_samples, has_sts_samples))
            
    return received_packet_dicts
        
        
    


def parse_packet(packet_bytes, has_acc_samples=False, has_sts_samples=False):    
    packet_dict = dict()
    pos = 0

    part = packet_bytes[pos:pos + DIAGNOSTIC_LEN]  
    pos += len(part)    

    packet_dict['diag'] = {}
    unpacked_data = struct.unpack('<' + DIAG_STRING_FORMAT, part)
    # Rx Status
    # 0: Success
    # 24: No strong rising edge on the first path
    # 25: Noise threshold had to be artificially lowered to find any first path
    # 26: CIR too weak to get any estimate
    # 27: Coarse first path estimate too close to end to be plausible
    # 28: First path too close to the end to be plausible        

    packet_dict['diag']['ipatovRxTime'] = int.from_bytes(unpacked_data[0:5], 'little') * DW_TIME_UNIT
    packet_dict['diag']['ipatovRxStatus'] = unpacked_data[5]                
    packet_dict['diag']['ipatovPOA'] = unpacked_data[6]

    packet_dict['diag']['stsRxTime'] = int.from_bytes(unpacked_data[7:12], 'little') * DW_TIME_UNIT

    packet_dict['diag']['stsRxStatus'] = unpacked_data[12]
    packet_dict['diag']['stsPOA'] = unpacked_data[13]
    packet_dict['diag']['sts2RxTime'] = int.from_bytes(unpacked_data[14:19], 'little') * DW_TIME_UNIT
    packet_dict['diag']['sts2RxStatus'] = unpacked_data[19]
    packet_dict['diag']['sts2POA'] = unpacked_data[20]

    packet_dict['diag']['tdoa'] = int.from_bytes(unpacked_data[21:27], 'little') * DW_TIME_UNIT
    packet_dict['diag']['pdoa'] = unpacked_data[27]

    packet_dict['diag']['xtalOffset'] = (unpacked_data[28] / (2**26)) * 10**6        
    packet_dict['diag']['ciaDiag1'] = unpacked_data[29]

    packet_dict['diag']['ipatovPeak'] = {}
    packet_dict['diag']['ipatovPeak']['peakIndex']= unpacked_data[30] >> 21 
    packet_dict['diag']['ipatovPeak']['peakAmplitude']= unpacked_data[30] & 0x1FFFF
    packet_dict['diag']['ipatovPower'] = unpacked_data[31]
    packet_dict['diag']['ipatovF1'] = unpacked_data[32]
    packet_dict['diag']['ipatovF2'] = unpacked_data[33]
    packet_dict['diag']['ipatovF3'] = unpacked_data[34]
    packet_dict['diag']['ipatovFpIndex'] = unpacked_data[35] >> 6
    packet_dict['diag']['ipatovAccumCount'] = unpacked_data[36]

    packet_dict['diag']['stsPeak'] = {}
    packet_dict['diag']['stsPeak']['peakIndex']= unpacked_data[37] >> 21 
    packet_dict['diag']['stsPeak']['peakAmplitude']= unpacked_data[37] & 0x1FFFF
    packet_dict['diag']['stsPower'] = unpacked_data[38]
    packet_dict['diag']['stsF1'] = unpacked_data[39]
    packet_dict['diag']['stsF2'] = unpacked_data[40]
    packet_dict['diag']['stsF3'] = unpacked_data[41]
    packet_dict['diag']['stsFpIndex'] = unpacked_data[42] >> 6
    packet_dict['diag']['stsAccumCount'] = unpacked_data[43]

    packet_dict['diag']['sts2Peak'] = {}
    packet_dict['diag']['sts2Peak']['peakIndex']= unpacked_data[44] >> 21 
    packet_dict['diag']['sts2Peak']['peakAmplitude']= unpacked_data[44] & 0x1FFFF
    packet_dict['diag']['sts2Power'] = unpacked_data[45]
    packet_dict['diag']['sts2F1'] = unpacked_data[46]
    packet_dict['diag']['sts2F2'] = unpacked_data[47]
    packet_dict['diag']['sts2F3'] = unpacked_data[48]
    packet_dict['diag']['sts2FpIndex'] = unpacked_data[49] >> 6
    packet_dict['diag']['sts2AccumCount'] = unpacked_data[50]

    part = packet_bytes[pos]
    pos += 1
    packet_dict['dgc_decision'] = part

    part = packet_bytes[pos:pos+4]
    pos += 4
    packet_dict['cfo'] = struct.unpack( "<f", part)[0]

    part = packet_bytes[pos:pos+4]
    pos += 4
    packet_dict['temperature'] = struct.unpack( "<f", part)[0]

    part = packet_bytes[pos:pos+4]
    pos += 4
    packet_dict['voltage'] = struct.unpack( "<f", part)[0]

    part = packet_bytes[pos:pos + RX_DATA_LEN]
    pos += len(part)        
    packet_dict['rx_data'] = dict()
    packet_dict['rx_data']['streamID'] = int.from_bytes(part[0:4], "little")
    packet_dict['rx_data']['seqNum'] = int.from_bytes(part[4:6], "little")
    packet_dict['rx_data']['FCS'] = part[6:]

    if has_acc_samples: 
        part = packet_bytes[pos:pos + ACC_DATA_LEN]
        pos += len(part)

        part = part[1:] # delete dummy data
        packet_dict['acc_data'] = dict()
        packet_dict['acc_data']['iValue'] = []
        packet_dict['acc_data']['qValue'] = []
        packet_dict['acc_data']['CIR'] = []

        for i in range(NUM_ACC_SAMPLES):
            iValue = part[(i*6)]
            iValue |= (part[(i*6)+1] << 8)
            iValue |= ((part[(i*6)+2] & 0x03) << 16)

            if iValue & 0x020000:
                iValue -=  0x040000

            qValue = part[(i*6)+3]
            qValue |= (part[(i*6)+4] << 8)
            qValue |= ((part[(i*6)+5] & 0x03) << 16)

            if qValue & 0x020000:
                qValue -=  0x040000

            packet_dict['acc_data']['iValue'].append(iValue)
            packet_dict['acc_data']['qValue'].append(qValue)            
            packet_dict['acc_data']['CIR'].append(math.sqrt(float(iValue*iValue + qValue*qValue)))

    if has_sts_samples: 
        part = packet_bytes[pos:pos + STS_DATA_LEN]
        pos += len(part)

        part = part[1:] # delete dummy data
        packet_dict['sts_data'] = dict()
        packet_dict['sts_data']['iValue'] = []
        packet_dict['sts_data']['qValue'] = []
        packet_dict['sts_data']['CIR'] = []

        for i in range(NUM_STS_SAMPLES):
            iValue = part[(i*6)]
            iValue |= (part[(i*6)+1] << 8)
            iValue |= ((part[(i*6)+2] & 0x03) << 16)

            if iValue & 0x020000:
                iValue -=  0x040000

                qValue = part[(i*6)+3]
                qValue |= (part[(i*6)+4] << 8)
                qValue |= ((part[(i*6)+5] & 0x03) << 16)

            if qValue & 0x020000:
                qValue -=  0x040000

            packet_dict['sts_data']['iValue'].append(iValue)
            packet_dict['sts_data']['qValue'].append(qValue)        
            packet_dict['sts_data']['CIR'].append(math.sqrt(float(iValue*iValue + qValue*qValue)))
            
    return packet_dict


def moving_average_np(data, window_size):
    if window_size > len(data):
        raise ValueError("Window size must be less than or equal to the length of the data")
    
    data = np.array(data)
    averages = np.convolve(data, np.ones(window_size), 'valid') / window_size
    return averages