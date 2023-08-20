import os
import time
import threading
from ctypes import *

VCI_USBCAN2 = 4
STATUS_OK = 1

class VCI_INIT_CONFIG(Structure):  
    _fields_ = [("AccCode", c_uint),
                ("AccMask", c_uint),
                ("Reserved", c_uint),
                ("Filter", c_ubyte),
                ("Timing0", c_ubyte),
                ("Timing1", c_ubyte),
                ("Mode", c_ubyte)
                ]  

class VCI_CAN_OBJ(Structure):  
    _fields_ = [("ID", c_uint),
                ("TimeStamp", c_uint),
                ("TimeFlag", c_ubyte),
                ("SendType", c_ubyte),
                ("RemoteFlag", c_ubyte),
                ("ExternFlag", c_ubyte),
                ("DataLen", c_ubyte),
                ("Data", c_ubyte*8),
                ("Reserved", c_ubyte*3)
                ] 

# define data types
class VCI_BOARD_INFO(Structure):
    _fields_ = [("hw_Version", c_ushort),
                ("fw_Version", c_ushort),
                ("dr_Version", c_ushort),
                ("in_Version", c_ushort),
                ("irq_Num", c_ushort),
                ("can_Num", c_byte),
                ("str_Serial_Num", c_char * 20),
                ("str_hw_Type", c_char * 40),
                ("Reserved", c_ushort * 4)]
    
# Append parent directory to import path, import file from parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
data_file = os.path.join(script_dir, 'libcontrolcan.so')
CANLib = cdll.LoadLibrary(data_file)

# find the number of connected devices
pInfo1 = (VCI_BOARD_INFO * 20)()  # Array of 20 VCI_BOARD_INFO structures
num = CANLib.VCI_FindUsbDevice2(pInfo1)


print(">>USBCAN DEVICE NUM:", num, "PCS")

# loop through each device and print its info
for i in range(num):
    print("Device:", i)
    print(">>Get VCI_ReadBoardInfo success!")
    print(">>Serial_Num:", pInfo1[i].str_Serial_Num.decode('ascii'))
    print(">>hw_Type:", pInfo1[i].str_hw_Type.decode('ascii'))

# open the device
ret = CANLib.VCI_OpenDevice(VCI_USBCAN2, 0, 0)
if ret == 1:
    print(">>open device success!")
else:
    print(">>open device error!")
    exit(1)

# read the board info
pInfo = VCI_BOARD_INFO()
if CANLib.VCI_ReadBoardInfo(VCI_USBCAN2, 0, byref(pInfo)) == 1:
    print(">>Get VCI_ReadBoardInfo success!")
    print(">>Serial_Num:", pInfo.str_Serial_Num.decode('ascii'))
    print(">>hw_Type:", pInfo.str_hw_Type.decode('ascii'))
    print(">>Firmware Version:V{}.{}.{}\r\n".format((pInfo.fw_Version & 0xF00) >> 8, (pInfo.fw_Version & 0xF0) >> 4, pInfo.fw_Version & 0xF))
else:
    print(">>Get VCI_ReadBoardInfo error!")
    exit(1)

#ret = CANLib.VCI_OpenDevice(VCI_USBCAN2, 0, 0)

if ret == STATUS_OK:
    print('调用 VCI_OpenDevice成功\r\n')
if ret != STATUS_OK:
    print('调用 VCI_OpenDevice出错\r\n')

vci_initconfig = VCI_INIT_CONFIG(0x00000000, 0xFFFFFFFF, 0, 0, 0x00, 0x1C, 0)
ret = CANLib.VCI_InitCAN(VCI_USBCAN2, 0, 0, byref(vci_initconfig))

if ret == STATUS_OK:
    print('调用 VCI_InitCAN1成功\r\n')
if ret != STATUS_OK:
    print('调用 VCI_InitCAN1出错\r\n')

ret = CANLib.VCI_StartCAN(VCI_USBCAN2, 0, 0)
if ret == STATUS_OK:
    print('调用 VCI_StartCAN1成功\r\n')
if ret != STATUS_OK:
    print('调用 VCI_StartCAN1出错\r\n')

ret = CANLib.VCI_InitCAN(VCI_USBCAN2, 0, 1, byref(vci_initconfig))
if ret == STATUS_OK:
    print('调用 VCI_InitCAN2 成功\r\n')
if ret != STATUS_OK:
    print('调用 VCI_InitCAN2 出错\r\n')

ret = CANLib.VCI_StartCAN(VCI_USBCAN2, 0, 1)
if ret == STATUS_OK:
    print('调用 VCI_StartCAN2 成功\r\n')
if ret != STATUS_OK:
    print('调用 VCI_StartCAN2 出错\r\n')

ubyte_array = c_ubyte*8
a = ubyte_array(1,2,3,4, 5, 6, 7, 8)
ubyte_3array = c_ubyte*3
b = ubyte_3array(0, 0 , 0)
vci_can_obj = VCI_CAN_OBJ(0x1, 0, 0, 1, 0, 0,  8, a, b)

ret = CANLib.VCI_Transmit(VCI_USBCAN2, 0, 1, byref(vci_can_obj), 1)
if ret == STATUS_OK:
    print('CAN1通道发送成功\r\n')
if ret != STATUS_OK:
    print('CAN1通道发送失败\r\n')

print("wait 5 seconds")
time.sleep(5)

def receive_func(run):
    reclen = 0
    rec = (VCI_CAN_OBJ * 3000)()
    count = 0
    ind = 0

    while run & 0x0f:
        if (reclen := CANLib.VCI_Receive(VCI_USBCAN2, 0, ind, rec, 3000, 100)) > 0:
            for j in range(reclen):
                print(f"Index:{count:04d}  ", end=""); count += 1
                print(f"CAN{ind+1} RX ID:0x{rec[j].ID:08X}", end="")
                if rec[j].ExternFlag == 0: print(" Standard ", end="")
                if rec[j].ExternFlag == 1: print(" Extend   ", end="")
                if rec[j].RemoteFlag == 0: print(" Data   ", end="")
                if rec[j].RemoteFlag == 1: print(" Remote ", end="")
                print(f"DLC:0x{rec[j].DataLen:02X}", end="")
                print(" data:0x", end="")
                for i in range(rec[j].DataLen):
                    print(f" {rec[j].Data[i]:02X}", end="")
                print(f" TimeStamp:0x{rec[j].TimeStamp:08X}")
        ind = not ind

    print("run thread exit")

run = 1
receive_thread = threading.Thread(target=receive_func, args=(run,))
receive_thread.start()

# To stop the receive thread, set run to 0
# run = 0