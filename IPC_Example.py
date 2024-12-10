import argparse
import threading
import IPC_Library
import time
import sys
import os
from IPC_Library import parse_hex_data, parse_string_data

GPIO_EXPORT_PATH = "/sys/class/gpio/export"
GPIO_UNEXPORT_PATH = "/sys/class/gpio/unexport"
GPIO_DIRECTION_PATH_TEMPLATE = "/sys/class/gpio/gpio{}/direction"
GPIO_VALUE_PATH_TEMPLATE = "/sys/class/gpio/gpio{}/value"
GPIO_BASE_PATH_TEMPLATE = "/sys/class/gpio/gpio{}"

FREQUENCIES = {
    1: 261.63,  # C
    2: 293.66,  # D
    3: 329.63,  # E
    4: 349.23,  # F
    5: 392.00,  # G
    6: 440.00,  # A
    7: 493.88,  # B
    8: 523.25   # C5
}

def is_gpio_exported(gpio_number):
    gpio_base_path = GPIO_BASE_PATH_TEMPLATE.format(gpio_number)
    return os.path.exists(gpio_base_path)

def export_gpio(gpio_number):
    if not is_gpio_exported(gpio_number):
        try:
            with open(GPIO_EXPORT_PATH, 'w') as export_file:
                export_file.write(str(gpio_number))
        except IOError as e:
            print(f"Error exporting GPIO {gpio_number}: {e}")
            sys.exit(1)

def unexport_gpio(gpio_number):
    try:
        with open(GPIO_UNEXPORT_PATH, 'w') as unexport_file:
            unexport_file.write(str(gpio_number))
    except IOError as e:
        print(f"Error unexporting GPIO {gpio_number}: {e}")
        sys.exit(1)

def set_gpio_direction(gpio_number, direction):
    gpio_direction_path = GPIO_DIRECTION_PATH_TEMPLATE.format(gpio_number)
    try:
        with open(gpio_direction_path, 'w') as direction_file:
            direction_file.write(direction)
    except IOError as e:
        print(f"Error setting GPIO {gpio_number} direction to {direction}: {e}")
        sys.exit(1)

def set_gpio_value(gpio_number, value):
    gpio_value_path = GPIO_VALUE_PATH_TEMPLATE.format(gpio_number)
    try:
        with open(gpio_value_path, 'w') as value_file:
            value_file.write(str(value))
    except IOError as e:
        print(f"Error setting GPIO {gpio_number} value to {value}: {e}")
        sys.exit(1)

def play_tone(gpio_number, frequency, duration):
    if frequency <= 0:
        print("Invalid frequency: Skipping tone")
        return
    
    period = 1.0 / frequency
    half_period = period / 2
    end_time = time.time() + duration

    while time.time() < end_time:
        set_gpio_value(gpio_number, 1)
        time.sleep(half_period)
        set_gpio_value(gpio_number, 0)
        time.sleep(half_period)

def ipc_listener(gpio_pin):
    while True:
        if IPC_Library.received_pucData:
            note = IPC_Library.received_pucData[0]  # 첫 번째 바이트로 음계 결정
            duration = 0.5  # 기본 재생 시간
            
            if note in FREQUENCIES:
                print(f"Playing tone for note {note} at frequency {FREQUENCIES[note]} Hz")
                play_tone(gpio_pin, FREQUENCIES[note], duration)
            else:
                print(f"Received unknown note: {note}")
            time.sleep(0.1)  # IPC 데이터 처리 후 잠시 대기


def sendtoCAN(channel, canId, sndDataHex):
    sndData = parse_hex_data(sndDataHex)
    uiLength = len(sndData)
    ret = IPC_Library.IPC_SendPacketWithIPCHeader("/dev/tcc_ipc_micom", channel, IPC_Library.TCC_IPC_CMD_CA72_EDUCATION_CAN_DEMO, IPC_Library.IPC_IPC_CMD_CA72_EDUCATION_CAN_DEMO_START, canId, sndData, uiLength)

def receiveFromCAN():
    micom_thread = threading.Thread(target=IPC_Library.IPC_ReceivePacketFromIPCHeader, args=("/dev/tcc_ipc_micom", 1))
    micom_thread.start()

def main():
    parser = argparse.ArgumentParser(description="IPC Sender/Receiver")
    parser.add_argument("mode", choices=["snd", "rev"], help="Specify 'snd' to send a packet or 'rev' to receive a packet.")
    parser.add_argument("--file_path", default="/dev/tcc_ipc_micom", help="File path for IPC communication")
    parser.add_argument("--channel", type=int, default=0, help="Specify the IPC channel.")
    parser.add_argument("--uiCmd1", type=int, default=IPC_Library.TCC_IPC_CMD_CA72_EDUCATION_CAN_DEMO, help="Value for uiCmd1")
    parser.add_argument("--uiCmd2", type=int, default=IPC_Library.IPC_IPC_CMD_CA72_EDUCATION_CAN_DEMO_START, help="Value for uiCmd2")
    parser.add_argument("--uiCmd3", type=int, default=1, help="Value for uiCmd3")
    parser.add_argument("--sndDataHex", type=str, help="Value for sndData as a hex string, e.g., '12345678'")
    parser.add_argument("--sndDataStr", type=str, help="Value for sndData as a string, e.g., 'Hello!!!'")
    parser.add_argument("--defaultHex", type=str, default="12345678", help="Default hex data if no sndDataHex provided")

    args = parser.parse_args()
    print(f"args.mode {args.mode} args.file_path {args.file_path} args.channel {args.channel}")

    gpio_pin = 89  # GPIO 핀 번호 설정 (음성 출력을 위한 핀)

    try:
        export_gpio(gpio_pin)
        set_gpio_direction(gpio_pin, "out")

        if args.mode == "snd":
            if args.uiCmd1 is None or args.uiCmd2 is None:
                print("Please provide values for uiCmd1 and uiCmd2.")
                return

            uiCmd1 = args.uiCmd1
            uiCmd2 = args.uiCmd2
            uiCmd3 = args.uiCmd3

            if args.sndDataHex:
                sndData = IPC_Library.parse_hex_data(args.sndDataHex)
            elif args.sndDataStr:
                sndData = IPC_Library.parse_string_data(args.sndDataStr)
            else:
                sndData = IPC_Library.parse_hex_data(args.defaultHex)

            uiLength = len(sndData)

            print(f"file_path: {args.file_path}")
            print(f"channel: {args.channel}")
            print(f"uiCmd1: {uiCmd1}")
            print(f"uiCmd2: {uiCmd2}")
            print(f"uiCmd3: {uiCmd3}") 
            print(f"sndData: {sndData}")
            print(f"uiLength: {uiLength}")

            sendtoCAN(args.channel, uiCmd1, args.sndDataHex)  # 송신 데이터 처리

        elif args.mode == "rev":
            # IPC 수신 처리 스레드 시작
            micom_thread = threading.Thread(target=IPC_Library.IPC_ReceivePacketFromIPCHeader, args=("/dev/tcc_ipc_micom", 1))
            micom_thread.start()

            # IPC 데이터를 통해 음을 재생하는 부분
            ipc_listener(gpio_pin)

        else:
            print("Invalid mode. Use 'snd' or 'rev'.")
            return

    except KeyboardInterrupt:
        print("\nOperation stopped by User")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        unexport_gpio(gpio_pin)

    sys.exit(0)

if __name__ == "__main__":
    main()
