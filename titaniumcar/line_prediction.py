import cv2
import numpy as np
from collections import deque

import math
import time

from picamera import PiCamera
from picamera.array import PiRGBAnalysis
from picamera.color import Color

from car import Car

class ProcessChain:
    def canny_trsf(self, image):
        """
        Applying a gaussian Blur to smooth the image
    	Applying an edge detection from an RGB image

        @param image: a RGB OpenCV image
        @return: the edges of image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        canny = cv2.Canny(blur, 20, 100)
        return canny

    def region_of_interest(self, image):
        """
        Set to (0, 0, 0) each pixel outside the roi

        @param image: a grayscale OpenCV image
        @return: the image with only roi
        """
        height = image.shape[0]
        # coordinates of the roi
        poly = np.array([
            (0, 131),
            (0, height),
            (454, height),
            (454, 131),
            (300, 94),
            (150, 94)
        ])
        mask = np.zeros_like(image)
        cv2.fillPoly(mask, (poly,), 255)
        masked_image = cv2.bitwise_and(image, mask)
        return masked_image
        
    def detect_lines(self, image):
        """
        Find the segments in the picture
        
        @param image: a grayscale OpenCV image with only bound
        @return: lines in a Numpy array  
        """
        lines = cv2.HoughLinesP(image, 3, np.pi/180, 100, np.array([]), minLineLength=37, maxLineGap=37)
        return lines
        
    def line_process(self, lines):
        """
        Find the point of convergence of lines
        The lines are filtered to keep only revelant lines
        
        @param lines: list or Numpy array with coordinates of lines
        @return: None if all lines are not revelant else float
        """
        if lines is None:
            return None

        lenghts = np.array([])
        origins = np.array([])
        nb_ignored = 0
        
        for line in lines:
            # get lenght of the line
            # and coordinate of intersection of line and abscissa
            x1, y1, x2, y2 = line.reshape(4)
            if y1 == y2:
                continue
            
            a = (x1-x2)/(y1-y2)
            b = x1 - a*y1
            
            lenght = np.sqrt(np.square(x1-x2)+np.square(y1-y2))
            # if intersection point if too away, remove it
            if 0-300 < b < 456+300:
                origins = np.append(origins, b)
                lenghts = np.append(lenghts, lenght)
            # when length is too small, the uncertainty of the direction is too large 
            # so, just increment counter
            elif lenght > 75:
                nb_ignored += 1
        
        if len(origins) == 0:
            return None
        else:
            pt_mean = np.average(origins, weights=lenghts)  
            
            # If the convergence point is on the sides,
            # the ignored lines could be revelant  
            if pt_mean > 0.5:
                pt_mean *= 1 + nb_ignored / 3
            return  pt_mean

    def transform(self, image):
        """
        Apply all transformations
        
        @param image: a OpenCV image of dimension (456, 228, 3)
        @return: mean direction of the edges of the circuit (float)
        """
        image = self.canny_trsf(image)
        image = self.region_of_interest(image)
        lines = self.detect_lines(image)
        
        return self.line_process(lines)

class Image2Prediction(PiRGBAnalysis):
    """
    Wrap the whole process from frame to apply predicted speed and direction
    """
    def __init__(self, camera, car):
        """
        Initialization of the attributes
        and create preprocess pipeline with ProcessChain class
        
        @param camera: PiCamera instance
        @param car: instance of Chassis or a child class
        """
        super().__init__(camera)
        self.done = False
        self.car = car
        self.default_direction = direction
        
        self.process = ProcessChain()
        self.queue = deque([0 for _ in range(12)])
    
    def analyze(self, frame):
        """
        For each frame, this method is called
        The steps are :
         * get the mean direction of the edges of the circuit  
         * predict the direction and the speed
         * apply the predicted speed and direction
        
        @param frame: a Numpy array usable like a OpenCV image
        """
        pt = self.process.transform(frame)
        if pt is not None:
            dir_prediction, speed_prediction = self.predict(pt)
            self.car.set_direction(dir_prediction)
            print(dir_prediction, speed_prediction)
        else:
            speed_prediction = 0.33
            print("None 0.33")
            
        self.car.set_speed(speed_prediction, force=True)  
        

    def predict(self, x, shape=(228, 456)):
        """
        Predict the speed and the direction with the taget point and the previous ones
        
        If the direction is straightforward for a while,
        the speed can be increase !
        
        @param x: the target point of the car
        @param shape: video frame dimensions in (y, x) format
        
        @return p_dir: the desired direction (between -1 and 1)
        @return p_speed: the desired speed (between -1 and 1)
        """
        # Normalize the point
        x = (x-shape[1]/2)/shape[1]
        
        # Compute the angle with origin
        p_dir = 2.5 * np.arctan(x)
        
        # FIFO (deque)
        self.queue.appendleft(p_dir)
        self.queue.pop()
        
        if p_dir > 1:
            p_dir = 1
        elif p_dir < -1:
            p_dir = -1
        
        # Get middle direction at the end of deque (oldest frame)
        # then at the beginning (newest frame)
        dA = np.mean([self.queue[i] for i in range(4)])
        dB = np.mean([self.queue[-i] for i in range(4)])
        
        # magic formula
        p_speed = 1 - (np.abs(dA)*0.9)
        print(p_speed)
        
        # p_speed *= 1-(np.abs(dA-dB)/2)**0.8
                
        return p_dir, p_speedmain


if __name__ == "__main__":
    car = Car().start()
    car.set_speed(1)

    with PiCamera(resolution=(456, 228), framerate=30) as camera:
        # Fix the camera's white-balance gains
        camera.awb_mode = 'off'
        camera.awb_gains = (1.4, 1.5)
        # Construct the analysis output and start recording data to it
        with Image2Prediction(camera, car) as i2p:
            camera.start_recording(i2p, 'rgb')
            try:
                while True:
                    camera.wait_recording(1)
            finally:
                camera.stop_recording()
