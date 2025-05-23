import network
import socket
from machine import Pin, PWM
import camera
import time
import json

# Define the GPIO pins for the servo motors
SERVO_PIN_X = 12  # Horizontal servo motor
SERVO_PIN_Y = 13  # Vertical servo motor

# Initialize the servos
servo_x = PWM(Pin(SERVO_PIN_X), freq=50)
servo_y = PWM(Pin(SERVO_PIN_Y), freq=50)

# Define servo position limits
MIN_DUTY = 40  # Minimum duty cycle (0 degrees)
MAX_DUTY = 115  # Maximum duty cycle (180 degrees)

def set_servo_position(servo, angle):
    duty = MIN_DUTY + (MAX_DUTY - MIN_DUTY) * (angle / 180)
    servo.duty(int(duty))

# Face tracking variables
face_center_x = 160  # Center of the camera frame
face_center_y = 120  # Center of the camera frame

LED_FLASH_PIN = 4  # GPIO pin for the built-in LED flash

def connect_to_wifi(ssid, password, max_attempts=10):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()  # Ensure the module is disconnected before trying to connect
    time.sleep(1)  # Wait a moment after disconnecting

    attempts = 0
    while not sta.isconnected() and attempts < max_attempts:
        print("Connecting to Wi-Fi...")
        sta.connect(ssid, password)
        attempts += 1
        time.sleep(2)  # Increased delay between attempts
        print("Attempt:", attempts)
        if sta.isconnected():
            print("Wi-Fi connected")
            break
    if not sta.isconnected():
        raise RuntimeError("Failed to connect to Wi-Fi")
    print("Connected to Wi-Fi:", ssid)
    ip_address = sta.ifconfig()[0]
    snapshotAPI = "http://" + str(ip_address) + "/snapshot"
    streamAPI = "http://" + str(ip_address) + "/stream"
    print("ESP32-Cam Snapshot API:", snapshotAPI)
    print("ESP32-Cam Stream API:", streamAPI)
    return ip_address

def initialize_camera():
    try:
        print("Initializing camera...")
        time.sleep(2)  # Add a delay to ensure the camera module is ready

        # Camera configuration
        camera.init(0, format=camera.JPEG)
        camera.framesize(camera.FRAME_QVGA)  # Set resolution to QVGA (320x240)
        camera.quality(10)  # Set JPEG quality (lower value means higher compression)
        camera.speffect(camera.EFFECT_NONE)  # Set effect to none

        print("Camera initialized successfully!")
    except Exception as e:
        print("Error initializing camera:", e)
        raise  # Re-raise the exception to see the full traceback

def handle_snapshot_request(client_socket):
    try:
        snapshot = camera.capture()
        if snapshot:
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: image/jpeg\r\n"
                "Content-Length: {}\r\n"
                "Connection: keep-alive\r\n\r\n".format(len(snapshot))
            )
            client_socket.send(response)
            client_socket.send(snapshot)
        else:
            client_socket.send("HTTP/1.1 500 Internal Server Error\r\n\r\n")
    except Exception as e:
        print("Error capturing image:", e)
        client_socket.send("HTTP/1.1 500 Internal Server Error\r\n\r\n")

def handle_stream_request(client_socket):
    try:
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
            "Connection: keep-alive\r\n\r\n"
        )
        client_socket.send(response)

        # Initialize last known servo positions
        last_servo_x_angle = 90
        last_servo_y_angle = 90

        while True:
            snapshot = camera.capture()
            if snapshot:
                frame_header = (
                    "--frame\r\n"
                    "Content-Type: image/jpeg\r\n"
                    "Content-Length: {}\r\n\r\n".format(len(snapshot))
                )
                client_socket.send(frame_header)
                client_socket.send(snapshot)
                client_socket.send("\r\n")
                time.sleep(0.05)  # Adjust the delay as needed for frame rate

                # Face tracking logic
                face_data = client_socket.recv(1024)
                if face_data:
                    face_json = json.loads(face_data.decode('utf-8'))
                    face_center_x = face_json['x']
                    face_center_y = face_json['y']

                    # Adjust servo positions based on face center
                    servo_x_angle = 90 + (face_center_x - 160) * 0.5
                    servo_y_angle = 90 + (face_center_y - 120) * 0.5

                    set_servo_position(servo_x, servo_x_angle)
                    set_servo_position(servo_y, servo_y_angle)

                    # Update last known servo positions
                    last_servo_x_angle = servo_x_angle
                    last_servo_y_angle = servo_y_angle
                else:
                    # If no face data received, maintain last known positions
                    set_servo_position(servo_x, last_servo_x_angle)
                    set_servo_position(servo_y, last_servo_y_angle)
            else:
                client_socket.send("HTTP/1.1 500 Internal Server Error\r\n\r\n")
                break
    except Exception as e:
        print("Error streaming video:", e)
    finally:
        client_socket.close()

def test_servos():
    try:
        # Move servo_x through 0 to 180 degrees
        for angle in range(0, 181, 10):
            set_servo_position(servo_x, angle)
            time.sleep(0.5)

        # Move servo_y through 0 to 180 degrees
        for angle in range(0, 181, 10):
            set_servo_position(servo_y, angle)
            time.sleep(0.5)

        # Move servos back to 90 degrees (neutral position)
        set_servo_position(servo_x, 90)
        set_servo_position(servo_y, 90)

    except Exception as e:
        print("Error:", e)

    finally:
        # Ensure servos stop moving after testing
        set_servo_position(servo_x, 0)
        set_servo_position(servo_y, 0)

def start_server(ip_address, port=80):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ip_address, port))
    server_socket.listen(5)  # Queue up to 5 connections
    print("Server started at {}:{}".format(ip_address, port))
    return server_socket

def main():
    try:
        ssid = "Hammad"
        password = "1234567800"
        ip_address = connect_to_wifi(ssid, password)
        initialize_camera()

        # Initialize servos to the neutral position
        set_servo_position(servo_x, 90)
        set_servo_position(servo_y, 90)

        server_socket = start_server(ip_address)
        while True:
            client_socket, addr = server_socket.accept()
            print("Client connected from:", addr)
            request = client_socket.recv(1024)
            if b"/snapshot" in request:
                handle_snapshot_request(client_socket)
            elif b"/stream" in request:
                handle_stream_request(client_socket)
            else:
                client_socket.send("HTTP/1.1 404 Not Found\r\n\r\n")
                client_socket.close()

    except Exception as e:
        print("Error in main:", e)

if __name__ == "__main__":
    test_servos()  # Run servo test first
    main()  # Then run the main server loop
