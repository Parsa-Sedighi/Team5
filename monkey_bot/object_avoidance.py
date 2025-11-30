#!/usr/bin/env python3
import cv2
import depthai as dai
import numpy as np
import serial

from movement_test import MotorSerialClient

# Tuning parameters
MIN_AREA = 500          # minimum contour area for a valid detection
SIDE_MARGIN = 25        # pixels around center that count as neutral zone


def find_color_center(frame_hsv, color_name):
    """
    Find the largest blob of a given color and return its center (cx, cy).
    Returns (None, None) if not found or too small.
    """
    if color_name == "red":
        # Red wraps around 0/180 in HSV, use two ranges
        lower1 = np.array([0, 120, 70])
        upper1 = np.array([10, 255, 255])
        lower2 = np.array([170, 120, 70])
        upper2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(frame_hsv, lower1, upper1)
        mask2 = cv2.inRange(frame_hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

    elif color_name == "blue":
        lower = np.array([100, 150, 50])
        upper = np.array([140, 255, 255])
        mask = cv2.inRange(frame_hsv, lower, upper)

    else:
        raise ValueError("Unsupported color: " + color_name)

    # Clean up noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    # Largest contour
    c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < MIN_AREA:
        return None, None

    x, y, w, h = cv2.boundingRect(c)
    cx = x + w // 2
    cy = y + h // 2
    return cx, cy


# ---------------- ROBOT CONTROL HOOKS ---------------- #

def move_left():
    print("CMD: MOVE LEFT")


def move_right():
    print("CMD: MOVE RIGHT")


def move_forward():
    print("CMD: MOVE FORWARD")


# ----------------------------------------------------- #

def main():
    # ---------- Arduino commands setup (Serial) ----------
    client = MotorSerialClient()

    # ---------- PIPELINE SETUP (DepthAI v2) ----------
    pipeline = dai.Pipeline()

    cam = pipeline.createColorCamera()
    cam.setPreviewSize(640, 480)
    cam.setInterleaved(False)
    cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

    xout = pipeline.createXLinkOut()
    xout.setStreamName("rgb")
    cam.preview.link(xout.input)

    # ---------- DEVICE / HOST LOOP ----------
    with dai.Device(pipeline) as device:
        q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        print("Running headless. Press Ctrl+C to stop.")

        try:
            while True:
                in_frame = q_rgb.get()
                frame = in_frame.getCvFrame()  # BGR image

                h, w = frame.shape[:2]
                center_x = w // 2

                # Convert to HSV
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # Find red and blue centers (anywhere in the frame)
                red_cx, red_cy = find_color_center(hsv, "red")
                blue_cx, blue_cy = find_color_center(hsv, "blue")

                            # Decide where they are relative to center
                command = None

                # 0) If BOTH: blue on LEFT and red on RIGHT -> go FORWARD
                if (
                blue_cx is not None and red_cx is not None
                and blue_cx < center_x - SIDE_MARGIN
                and red_cx > center_x + SIDE_MARGIN
                ):
                    command = "FORWARD"

                # 1) If red is on the RIGHT → move LEFT
                elif red_cx is not None and red_cx > center_x + SIDE_MARGIN:
                    command = "LEFT"

                # 2) Else if blue is on the LEFT → move RIGHT
                elif blue_cx is not None and blue_cx < center_x - SIDE_MARGIN:
                    command = "RIGHT"

                # 3) Else, default → move FORWARD
                else:
                    command = "FORWARD"

                # Execute command
                if command == "LEFT":
                    move_left()
                    client.set_motors(30, -30)
                elif command == "RIGHT":
                    move_right()
                    client.set_motors(-30, 30)
                else:
                    move_forward()
                    client.set_motors(30, 30)

                # Optional debug:
                # print(f"red_cx={red_cx}, blue_cx={blue_cx}, center_x={center_x}, cmd={command}")

        finally:
            # Make sure we stop the motors if the script exits
            client.set_motors(0, 0)


if __name__ == "__main__":
    main()