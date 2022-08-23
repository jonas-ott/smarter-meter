#!/usr/bin/env python3

import numpy as np
import cv2


def nothing(x):
    pass


def main():
    cv2.namedWindow('image')

    cv2.createTrackbar('area_min', 'image', 1500, 9999, nothing)

    cv2.createTrackbar('x_min', 'image', 0, 640, nothing)
    cv2.createTrackbar('y_min', 'image', 122, 480, nothing)
    cv2.createTrackbar('x_max', 'image', 394, 640, nothing)
    cv2.createTrackbar('y_max', 'image', 219, 480, nothing)

    cv2.createTrackbar('h_min', 'image', 161, 179, nothing)
    cv2.createTrackbar('h_max', 'image', 179, 179, nothing)
    cv2.createTrackbar('s_min', 'image', 108, 255, nothing)
    cv2.createTrackbar('s_max', 'image', 216, 255, nothing)
    cv2.createTrackbar('v_min', 'image', 45, 255, nothing)
    cv2.createTrackbar('v_max', 'image', 128, 255, nothing)

    while True:
        image_frame = cv2.imread("calib.jpg")
        hsv_frame = cv2.cvtColor(image_frame, cv2.COLOR_BGR2HSV)

        # Mask Area for detection
        min_area = cv2.getTrackbarPos('area_min', 'image')
        x_min = cv2.getTrackbarPos('x_min', 'image')
        y_min = cv2.getTrackbarPos('y_min', 'image')
        x_max = cv2.getTrackbarPos('x_max', 'image')
        y_max = cv2.getTrackbarPos('y_max', 'image')

        mask = np.zeros(hsv_frame.shape[:2], dtype="uint8")
        cv2.rectangle(mask, (x_min, y_min), (x_max, y_max), 255, -1)
        cv2.rectangle(image_frame, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
        hsv_frame = cv2.bitwise_and(hsv_frame, hsv_frame, mask=mask)

        h_min = cv2.getTrackbarPos('h_min', 'image')
        h_max = cv2.getTrackbarPos('h_max', 'image')
        s_min = cv2.getTrackbarPos('s_min', 'image')
        s_max = cv2.getTrackbarPos('s_max', 'image')
        v_min = cv2.getTrackbarPos('v_min', 'image')
        v_max = cv2.getTrackbarPos('v_max', 'image')

        # Set range and define mask
        red_lower = np.array([h_min, s_min, v_min], np.uint8)
        red_upper = np.array([h_max, s_max, v_max], np.uint8)

        red_mask = cv2.inRange(hsv_frame, red_lower, red_upper)

        red_mask = cv2.dilate(red_mask, np.ones((5, 5), "uint8"))
        cv2.bitwise_and(image_frame, image_frame, mask=red_mask)

        # Creating contour to track red color
        contours, hierarchy = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            max_area = 0
            max_contour = contours[0]

            for pic, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > max_area:
                    max_area = area
                    max_contour = contour

            if max_area > min_area:
                x, y, w, h = cv2.boundingRect(max_contour)
                cv2.rectangle(image_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(image_frame, str(max_area), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255))

        cv2.imshow('image', image_frame)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            print("""
MIN_AREA = {}

X_MIN = {}
Y_MIN = {}
X_MAX = {}
Y_MAX = {}

H_MIN = {}
H_MAX = {}
S_MIN = {}
S_MAX = {}
V_MIN = {}
V_MAX = {}
""".format(min_area, x_min, y_min, x_max, y_max, h_min, h_max, s_min, s_max, v_min, v_max))
            cv2.destroyAllWindows()
            break


if __name__ == "__main__":
    main()
