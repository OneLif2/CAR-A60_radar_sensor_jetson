import os
import time
import threading
from ctypes import *


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


class CANDevice:
    VCI_USBCAN2 = 4
    STATUS_OK = 1

    def __init__(self, script_dir):
        data_file = os.path.join(script_dir, 'libcontrolcan.so')
        self.CANLib = cdll.LoadLibrary(data_file)
        self.run = 1
        self.rxid = 0

    def open_device(self):
        # Array of 20 VCI_BOARD_INFO structures
        pInfo1 = (VCI_BOARD_INFO * 20)()
        num = self.CANLib.VCI_FindUsbDevice2(pInfo1)
        print(">>USBCAN DEVICE NUM:", num, "PCS")

        # loop through each device and print its info
        for i in range(num):
            print("Device:", i)
            print(">>Get VCI_ReadBoardInfo success!")
            print(">>Serial_Num:", pInfo1[i].str_Serial_Num.decode('ascii'))
            print(">>hw_Type:", pInfo1[i].str_hw_Type.decode('ascii'))
            print(">>")
            print(">>")

        # open the device
        ret = self.CANLib.VCI_OpenDevice(self.VCI_USBCAN2, 0, 0)
        if ret == 1:
            print(">>open device success!\n")
            return True
        else:
            print(">>open device error!\n")
            return False

    def read_board_info(self):
        # read the board info
        pInfo = VCI_BOARD_INFO()
        if self.CANLib.VCI_ReadBoardInfo(self.VCI_USBCAN2, 0, byref(pInfo)) == 1:
            print(">>Get VCI_ReadBoardInfo success!")
            print(">>Serial_Num:", pInfo.str_Serial_Num.decode('ascii'))
            print(">>hw_Type:", pInfo.str_hw_Type.decode('ascii'))
            print(">>Firmware Version:V{}.{}{}\n".format((pInfo.fw_Version & 0xF00)
                  >> 8, (pInfo.fw_Version & 0xF0) >> 4, pInfo.fw_Version & 0xF))
            return True
        else:
            print(">>Get VCI_ReadBoardInfo error!")
            return False

    def convert_60b(self, int_arr, data_obj):
        ID = int_arr[0]
        lng_dis = (int_arr[1]*32 + (int_arr[2] >> 3))*0.2 - 500
        tvs_dis = ((int_arr[2] & 0x07)*256 + int_arr[3])*0.2 - 204.6
        tar_lng_velocity = (int_arr[4]*4 + (int_arr[5] >> 6)) * 0.25 - 128
        tar_lat_velocity = ((int_arr[5] & 0x3F)*8 + (int_arr[6] >> 5)) * 0.25 - 64
        tar_dy_attd = int_arr[6] & 0x07
        rcs = int_arr[7]*0.5 - 64

        print("\n")
        print(f"Target ID: {ID}")
        print(f"Longtitudinal distance(Y): {lng_dis} m")
        print(f"Transverse distance(X): {tvs_dis} m")
        print(f"Target longitudinal(Y) velocity: {tar_lng_velocity} m/s")
        print(f"Target lateral(X) velocity: {tar_lat_velocity} m/s")
        print(f"Target dynamic attribute: {tar_dy_attd}")
        print(f"RCS: {rcs}")
        print(f"TimeStamp:0x{data_obj.TimeStamp:08X}","\n")

    def receive_func(self):
        reclen = 0
        rec = (VCI_CAN_OBJ * 3000)()
        count = 0
        ind = 0

        while self.run & 0x0f:
            reclen = self.CANLib.VCI_Receive(self.VCI_USBCAN2, 0, ind, rec, 3000, 100)
            if reclen > 0:
                for j in range(reclen):
                    self.rxid = rec[j].ID
                    int_arr = []
                    for i in range(rec[j].DataLen):
                        int_arr.append(rec[j].Data[i])  # convert to int array

                    print(f"Index:{count:04d}  ", end="")
                    count += 1

                    if self.rxid == 0x60b:
                        self.convert_60b(int_arr, rec[j])
                    else:
                        print(f"CAN{ind+1} RX ID:{hex(self.rxid)}", end="")
                        if rec[j].ExternFlag == 0:
                            print(" Standard ", end="")
                        if rec[j].ExternFlag == 1:
                            print(" Extend   ", end="")
                        if rec[j].RemoteFlag == 0:
                            print(" Data | ", end="")
                        if rec[j].RemoteFlag == 1:
                            print(" Remote | ", end="")
                        print(f"DLC:0x{rec[j].DataLen:02X}", end="")
                        print(" data:", end="")
                        hex_int_arr = ["{:02x}".format(num) for num in int_arr]
                        print(hex_int_arr, end="")
                        print(f" TimeStamp:0x{rec[j].TimeStamp:08X}")
            ind = not ind
        print("run thread exit")

    def start_receive_thread(self):
        self.receive_thread = threading.Thread(target=self.receive_func)
        self.receive_thread.start()

    def stop_receive_thread(self):
        self.run = 1

    def openDevice(self):
        vci_initconfig = VCI_INIT_CONFIG(
            0x00000000, 0xFFFFFFFF, 0, 0, 0x00, 0x1C, 0)
        ret = self.CANLib.VCI_InitCAN(
            self.VCI_USBCAN2, 0, 0, byref(vci_initconfig))

        if ret == self.STATUS_OK:
            print('调用 VCI_OpenDevice成功')
        if ret != self.STATUS_OK:
            print('调用 VCI_OpenDevice出错')

        ret = self.CANLib.VCI_InitCAN(
            self.VCI_USBCAN2, 0, 0, byref(vci_initconfig))
        if ret == self.STATUS_OK:
            print('调用 VCI_InitCAN1成功')
        if ret != self.STATUS_OK:
            print('调用 VCI_InitCAN1出错')

        ret = self.CANLib.VCI_StartCAN(self.VCI_USBCAN2, 0, 0)
        if ret == self.STATUS_OK:
            print('调用 VCI_StartCAN1成功')
        if ret != self.STATUS_OK:
            print('调用 VCI_StartCAN1出错')

        ret = self.CANLib.VCI_InitCAN(
            self.VCI_USBCAN2, 0, 1, byref(vci_initconfig))
        if ret == self.STATUS_OK:
            print('调用 VCI_InitCAN2 成功')
        if ret != self.STATUS_OK:
            print('调用 VCI_InitCAN2 出错')

        ret = self.CANLib.VCI_StartCAN(self.VCI_USBCAN2, 0, 1)
        if ret == self.STATUS_OK:
            print('调用 VCI_StartCAN2 成功')
        if ret != self.STATUS_OK:
            print('调用 VCI_StartCAN2 出错')

        ubyte_array = c_ubyte*8
        a = ubyte_array(1, 2, 3, 4, 5, 6, 7, 8)
        ubyte_3array = c_ubyte*3
        b = ubyte_3array(0, 0, 0)
        vci_can_obj = VCI_CAN_OBJ(0x1, 0, 0, 1, 0, 0,  8, a, b)

        ret = self.CANLib.VCI_Transmit(
            self.VCI_USBCAN2, 0, 1, byref(vci_can_obj), 1)
        if ret == self.STATUS_OK:
            print('CAN1通道发送成功\n')
        if ret != self.STATUS_OK:
            print('CAN1通道发送失败\n')


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    device = CANDevice(script_dir)
    try:
        if device.open_device() and device.read_board_info():
            device.openDevice()
            print("wait 5 seconds")
            time.sleep(2)
            device.start_receive_thread()
            device.stop_receive_thread()
    except KeyboardInterrupt:
        print("\nCtrl+C detected, closing device...")
        device.CANLib.VCI_CloseDevice(device.VCI_USBCAN2, 0)
        try:
            device.CANLib.VCI_CloseDevice(device.VCI_USBCAN2, 0)
            print("Device closed successfully")
        except Exception as e:
            print(f"Error closing device: {e}")
            device.CANLib.VCI_CloseDevice(device.VCI_USBCAN2, 0)
        exit(0)


if __name__ == "__main__":
    main()
