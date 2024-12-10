import sys
import os
import time
import threading
import IPC_Library  # IPC 라이브러리 임포트

GPIO_EXPORT_PATH = "/sys/class/gpio/export"
GPIO_UNEXPORT_PATH = "/sys/class/gpio/unexport"
GPIO_DIRECTION_PATH_TEMPLATE = "/sys/class/gpio/gpio{}/direction"
GPIO_VALUE_PATH_TEMPLATE = "/sys/class/gpio/gpio{}/value"
GPIO_BASE_PATH_TEMPLATE = "/sys/class/gpio/gpio{}"

FREQUENCIES = {
    'C': 261.63,  
    'D': 293.66,  
    'E': 329.63,  
    'F': 349.23,  
    'G': 392.00,  
    'A': 440.00,  
    'B': 493.88,  
    'C5': 523.25  
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
    period = 1.0 / frequency
    half_period = period / 2
    end_time = time.time() + duration

    while time.time() < end_time:
        set_gpio_value(gpio_number, 1)  # 부저 울림
        time.sleep(half_period)
        set_gpio_value(gpio_number, 0)  # 부저 끔
        time.sleep(half_period)

def ipc_listener(gpio_number):
    file_path = "/dev/tcc_ipc_micom"  # IPC 채널 파일 경로
    IPC_Library.IPC_ReceivePacketFromIPCHeader(file_path, 1)  # IPC 패킷 수신
    
    while True:
        if IPC_Library.received_pucData:
            print("Received IPC data:", ' '.join(format(byte, '02X') for byte in IPC_Library.received_pucData))
            # 수신된 데이터의 첫 번째 바이트에 따라 주파수를 설정
            note = chr(IPC_Library.received_pucData[0])  # 첫 번째 바이트를 문자로 변환
            frequency = FREQUENCIES.get(note, 261.63)  # 기본 주파수는 'C'
            print(f"Playing tone at {frequency} Hz")
            play_tone(gpio_number, frequency, 0.5)  # 부저 울림

if __name__ == "__main__":
    gpio_pin = 18  # GPIO 18을 사용

    try:
        export_gpio(gpio_pin)
        set_gpio_direction(gpio_pin, "out")

        # IPC 리스너 스레드 시작
        ipc_thread = threading.Thread(target=ipc_listener, args=(gpio_pin,), daemon=True)
        ipc_thread.start()

        # 메인 루프
        while True:
            time.sleep(1)  # 다른 작업을 수행할 수 있는 공간

    except KeyboardInterrupt:
        print("\nOperation stopped by User")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        unexport_gpio(gpio_pin)

    sys.exit(0)
