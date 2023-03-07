#!/usr/bin/env python3

import time
import signal
from datetime import datetime
import numpy as np
import cv2
from picamera2 import Picamera2
import paho.mqtt.client as mqtt

# Adjust as necessary
MIN_AREA = 1500

X_MIN = 0
Y_MIN = 122
X_MAX = 394
Y_MAX = 219

H_MIN = 161
H_MAX = 179
S_MIN = 108
S_MAX = 216
V_MIN = 45
V_MAX = 128

MQTT_BROKER = "192.168.178.39"
MQTT_TOPIC = "smarter-meter/power"
TURN_INC = 1 / 75


# https://stackoverflow.com/a/31464349
class GracefulKiller:
    run = True

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.run = False


class Counter(object):

    def __init__(self):
        self.logfile = open("log/log.csv", 'a')
        self.hits = 0
        self.hit_time = 0
        self.none_time = 0
        self.counted = False
        self.last_flush = 0
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(MQTT_BROKER, 1883, 3600)
        self.last_time = datetime.min

    def __del__(self):
        self.logfile.close()

    def count(self):
        self.none_time = 0
        self.hits += 1

        if self.hits == 1:
            self.hit_time = time.clock_gettime(0)

        if self.hits >= 1 and (time.clock_gettime(0) - self.hit_time) > 0.05 and not self.counted:
            self.counted = True
            now = datetime.now()
            power = int(1000 * TURN_INC * 60 * 60 / (now - self.last_time).total_seconds())
            self.mqtt_client.publish(MQTT_TOPIC, power)
            self.last_time = now
            current_time = now.strftime('%Y-%m-%d %H:%M:%S.%f')
            self.logfile.write(current_time + '\n')

            if time.clock_gettime(0) - self.last_flush > 15 * 60:
                self.last_flush = time.clock_gettime(0)
                self.logfile.flush()

    def none(self):
        if self.none_time == 0:
            self.none_time = time.clock_gettime(0)
            self.hits = 0
            self.hit_time = 0

        if (time.clock_gettime(0) - self.none_time) > 2:
            self.counted = False


def main():
    killer = GracefulKiller()
    count = Counter()

    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
    picam2.start()
    # 12-15fps
    picam2.set_controls({"FrameDurationLimits": (66666, 83333)})

    while killer.run:
        image_frame = picam2.capture_array()
        hsv_frame = cv2.cvtColor(image_frame, cv2.COLOR_BGR2HSV)

        # https://www.geeksforgeeks.org/multiple-color-detection-in-real-time-using-python-opencv/
        mask = np.zeros(hsv_frame.shape[:2], dtype="uint8")
        cv2.rectangle(mask, (X_MIN, Y_MIN), (X_MAX, Y_MAX), 255, -1)
        cv2.rectangle(image_frame, (X_MIN, Y_MIN), (X_MAX, Y_MAX), (255, 0, 0), 2)
        hsv_frame = cv2.bitwise_and(hsv_frame, hsv_frame, mask=mask)

        # Set range and define mask
        red_lower = np.array([H_MIN, S_MIN, V_MIN], np.uint8)
        red_upper = np.array([H_MAX, S_MAX, V_MAX], np.uint8)
        red_mask = cv2.inRange(hsv_frame, red_lower, red_upper)

        red_mask = cv2.dilate(red_mask, np.ones((5, 5), "uint8"))
        cv2.bitwise_and(image_frame, image_frame, mask=red_mask)

        # Creating contour to track red color
        contours, hierarchy = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            max_area = 0

            for pic, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > max_area:
                    max_area = area

            if max_area > MIN_AREA:
                count.count()
            else:
                count.none()
        else:
            count.none()


if __name__ == "__main__":
    main()
