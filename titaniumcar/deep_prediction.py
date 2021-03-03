import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import load_model

import cv2
import numpy as np

from picamera import PiCamera
from picamera.array import PiRGBAnalysis
from picamera.color import Color

from f1 import Car

import time

session = tf.Session()
keras.backend.set_session(session)

"""
The image resolution is not correctly handled if it is no longer (456, 228).
"""

class CannyTrsf:
    """
    Applying a gaussian Blur to smooth the image
    Applying an edge detection from an RGB image
    """
    def __init__(self, blur_size=5):
        """
        Attribute initialization

        @param blur_size: the kernel size for gaussian blur
        """
        self.blur_size = (blur_size, blur_size)
    
    def __call__(self, image):
        """
        Apply the transformation

        @param image: a RGB OpenCV image
        @return: image's edges
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, self.blur_size, 0)
        canny = cv2.Canny(blur, 20, 100)
        return canny
  
    
class ROISelection:
    """
    Set to (0, 0, 0) each pixel outside the roi
    """
    def __init__(self, poly):
        """
        Attribute initialization

        @param poly: an array of coordinates for roi
        """
        self.poly = poly
        
    def __call__(self, image):
        """
        Apply the transformation

        @param image: a grayscale OpenCV image
        @return: the image with only roi
        """
        mask = np.zeros_like(image)
        cv2.fillPoly(mask, (self.poly,), 255)
        masked_image = cv2.bitwise_and(image, mask)
        return masked_image

    
class Resize():
    """
    Divide by 2 the image dimensions
    """
    def __call__(self, sample):
        """
        Apply the transformation

        @param image: a OpenCV image
        @return: the resized image
        """
        image = cv2.resize(sample, (0,0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        return image


class Crop:
    """
    Remove pixels on the top and the right
    """
    def __call__(self, sample):
        """
        Apply the transformation

        @param image: a OpenCV image
        @return: the cropped image
        """
        width = sample.shape[1]
        return sample[45:, :width-5]
    
       
class Normalize():
    """
    Normalized the image with mean of 0 and std of 1
    """
    def __call__(self, sample):
        """
        Apply the transformation
        
        @param image: a grayscale OpenCV image
        @return: a Numpy array normalized image with dimension of (69, 223, 1)
        """
        image = sample
        norm_img = np.zeros(image.shape)
        norm_img = cv2.normalize(image, norm_img, 0, 1, cv2.NORM_MINMAX)
        norm_img = norm_img.reshape(69, 223, -1)
        
        return norm_img


class ToTensor:
    """
    Add the batch dimension in axis 0
    """
    def __call__(self, sample):
        """
        Apply the transformation
        
        @param image: a Numpy array of dimension (69, 223, 1)
        @return: a Numpy array of dimension (1, 69, 223, 1)
        """
        image = sample.reshape(-1, 69, 223, 1)
        return image


class ProcessChain:
    """
    Create the preprocess pipeline before going in the CNN.
    Each element must be callable.
    Take care about the dimension between the return and the argument for the next class.
    """
    def __init__(self):
        """
        Initialization of the preprocess pipeline, "line"
        """
        self.line = [
            CannyTrsf(),
            ROISelection(
            	# Your ROI could be different depending of the camera orientation
            	# and the size of the returned image
                np.array([(0, 131), (0, 228), (450, 228), (450, 131), (300, 94), (150, 94)])
            ),
            Resize(),
            Crop(),
            Normalize(),
            ToTensor()
        ]

    def transform(self, image):
        """
        Iterate through "line" and return the last item
        
        @param image: a OpenCV image of dimension (456, 228, 3)
        @return: a Numpy array of dimension (1, 69, 223, 1)
        """
        item = image
        for process in self.line:
            item = process(item)
        
        return item
    
    def transform_and_save(self, image):
        """
        Iterate through "line" keep all intermediate items
        and return the last one
        Used for debugging
        
        @param image: a OpenCV image of dimension (456, 228, 3)
        @return item: a Numpy array of dimension (1, 69, 223, 1)
        @return change_keeper: a list with each preprocess step
        """
        change_keeper = []
        item = image
        for process in self.line:
            item = process(item)
            change_keeper.append(item)
        
        return item, change_keeper
        
class Image2Prediction(PiRGBAnalysis):
    """
    Wrap the whole process from frame to apply predicted speed and direction
    """
    def __init__(self, camera, car, model, output=None, record=False):
        """
        Initialization of the attributes
        and create preprocess pipeline with ProcessChain class
        
        output and record are not used in the final version
        
        @param camera: PiCamera instance
        @param car: instance of Chassis or a child class
        @param model: regression to predict a speed and a direction
        """
        super().__init__(camera)
        
        self.car = car
        self.process = ProcessChain()
        
        self.output_vid = output
        self.record = record
        
        self.model = model
        
    def analyze(self, frame):
        """
        For each frame, this method is called
        The steps are :
         * preprocess the image
         * put the image in CNN
         * apply the predicted speed and direction
        
        @param frame: a Numpy array usable like a OpenCV image
        """
        with session.as_default():
            frame = self.process.transform(frame)
            p_dir, p_speed = self.model.predict(frame.astype(np.float32))[0]
            
            # Magic numbers to shift the speed
            p_speed = 1.2*p_speed - 0.2
            
            print(p_dir, p_speed)
            
            self.car.set_direction(p_dir)
            self.car.set_speed(p_speed)
        
        
def build_model():
    """
    Create and load the CNN model that was trained before
    
    @return: the Keras model
    """
    model = keras.Sequential([
        layers.Conv2D(3, (3, 3), padding="valid", activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        
        layers.Conv2D(3, (3, 3), padding="valid", activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        
        layers.Conv2D(3, (3, 3), padding="valid", activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        
        layers.Flatten(),
        
        layers.Dense(50, activation="relu"),
        layers.Dense(8, activation="relu"),
        layers.Dense(2, activation=None),
    ])
    model.build((1, 69, 223, 1))
    model.load_weights('weights_last.h5')

    # Check if the ouput values is not NAN
    test = np.random.rand(1, 69, 223, 1)    
    print(model.predict(test))
    
    return model
        
if __name__ == "__main__":
    car = Car().start()
    out = cv2.VideoWriter('vid.avi',cv2.VideoWriter_fourcc(*"MJPG"), 5, (456,228))
    model = build_model()

    with PiCamera(resolution=(456, 228), framerate=30) as camera:
        # Fix the camera's white-balance gains
        camera.awb_mode = 'off'
        camera.awb_gains = (1.4, 1.5)
        # Construct the analysis output and start recording data to it
        with Image2Prediction(camera, car, model, output=out) as i2p:
            camera.start_recording(i2p, 'rgb')
            try:
                while True:
                    camera.wait_recording(1)
            finally:
                camera.stop_recording()
        
        
