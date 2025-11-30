#!/usr/bin/env python3
"""
Talks to your Arduino BTS7960 sketch.

Arduino code expects: "motor1,motor2\n"
where motor1 and motor2 are ints in range [-255, 255].
"""

import time
import serial

# === CONFIGURE THIS IF NEEDED ===
PORT = "/dev/ttyACM0"   # Common on Linux/RPi; change if needed
BAUDRATE = 9600
TIMEOUT = 1.0           # seconds for read timeout

# Class for interfacing between arduino and raspberry pi
class MotorSerialClient:
    # Initializing serial ports
    def __init__(self, port=PORT, baudrate=BAUDRATE, timeout=TIMEOUT):
        # Establish the serial port to the Arduino Uno, ensuring baudrates and port is correct
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        # Give Arduino a moment to reset after opening serial
        time.sleep(2.0)

        # Optional: flush any startup text
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    # Format the PWM values correctly for Arduino to read once it is sent/written on serial
    def set_motors(self, m1, m2):
        """
        Set both motors.
        m1 = Motor 1 value  [-255..255]
        m2 = Motor 2 value  [-255..255]
        """
        # Clamp just in case
        m1 = max(-255, min(255, int(m1)))
        m2 = max(-255, min(255, int(m2)))
        # Format the lines
        line = f"{m1},{m2}\n"
        # Write into serial port using the ascii characters
        self.ser.write(line.encode("ascii"))
        # To ensure that all data currently in the serial output buffer is sent to the connected device, blocking until all bytes are written:
        self.ser.flush()

    # Read from the Arduino 
    def read_line(self):
        """
        Read one line of feedback from Arduino (non-blocking-ish).
        Returns a string or None on timeout.
        """
        line = self.ser.readline().decode(errors="ignore").strip()
        return line if line else None
    # Close the serial port
    def close(self):
        self.ser.close()
# Hardcoded, predetermined movements
def simple_test_pattern():
    """
    Demo pattern:
      - Motors forward
      - Spin in place
      - Stop
    """
    client = MotorSerialClient()
    try:
        print("Connected, sending test pattern...")

        # Forward (both positive)
        print("Forward...")
        client.set_motors(150, 150)
        time.sleep(2)

        # Spin in place (one forward, one backward)
        print("Spin left...")
        client.set_motors(-150, 150)
        time.sleep(2)

        # Reverse
        print("Reverse...")
        client.set_motors(-150, -150)
        time.sleep(2)

        # Stop
        print("Stop.")
        client.set_motors(0, 0)
        time.sleep(1)

    finally:
        client.set_motors(0, 0)  # safety stop
        client.close()
        print("Disconnected.")

# Interactive 
def interactive_cli():
    """
    Simple interactive terminal:
    Type:  m1 m2
    Example:  120 -100
    """
    client = MotorSerialClient()
    try:
        print("Interactive mode. Type: m1 m2  (e.g. 120 -100)")
        print("Ctrl+C to quit; motors will be stopped on exit.")

        while True:
            try:
                raw = input("m1 m2 > ")
            except (EOFError, KeyboardInterrupt):
                break

            parts = raw.strip().split()
            if len(parts) != 2:
                print("Please enter two numbers, e.g. `150 -150`")
                continue

            try:
                m1 = int(parts[0])
                m2 = int(parts[1])
            except ValueError:
                print("Both values must be integers.")
                continue

            client.set_motors(m1, m2)
            # Optionally show Arduino's response (every ~500ms in your sketch)
            line = client.read_line()
            if line:
                print("[Arduino]", line)

    finally:
        client.set_motors(0, 0)
        client.close()
        print("\nMotors stopped, serial closed.")


if __name__ == "__main__":
    # Pick one:
    # simple_test_pattern()
    interactive_cli()