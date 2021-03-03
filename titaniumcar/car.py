from threading import Thread, Lock
from math import log

import cv2
import numpy as np
from time import sleep, time

class Chassis:
    """
    The lightest class to implement interface to control the car.
    
    The methods to reimplement are :
        - compute_speed
        - compute_direction
        
        In these methods, firstly, the current value must follow the variation of the targeted value.
        On the other hand, the pwm must be computed and returned with the current value.
        
    "set_speed" and "set_direction" methods shouldn't be rewritten
    to preserve the abstraction of the interface.
        
    The speed/direction dictionary could have new key/value.
    """
    def __init__(self):
        """
        Attribute initialization
        """
        self.speed = {
            "range_pwm": (375, 409, 413), # Be careful, wrong values could destroy the car.
            "current": 0,
            "target":  0,
            "pin": 5,
            
        }
        
        self.direction = {
            "range_pwm": (315, 410, 530),
            "current": 0,
            "target":  0,
            "pin": 15,
            
        }
        
        self.speed_lock = Lock()
        self.dir_lock = Lock()
        
        # Connection initialization with servos 
        try:
            from Adafruit_PCA9685 import PCA9685

            self.pwm = PCA9685()
            self.pwm.set_pwm_freq(60)
        except Exception as e:
            print("Error :", e)


    def start(self):
        """
        Start moving loop.
        
        Return the object to chain the declaration and the start
        car = Chassis().start()
        
        @return: itself after init
        """
        self.high_speed_trace = 0
    
        self.move_thread = Thread(target=self._moving_loop, args=())
        self.move_thread.start()
        
        return self
        
    
    def _moving_loop(self):
        """
        Compute then apply.
        We insert a little delay after to prevent fits and starts during course correction
        """
        
        while True:
            pwm = self.compute_speed()
            self.pwm.set_pwm(self.speed["pin"], 0, int(pwm))
            
            pwm = self.compute_direction()
            self.pwm.set_pwm(self.direction["pin"], 0, int(pwm))
            
            sleep(0.01)
    
    def compute_speed(self):
        """
        Set the current value with the target.
        Compute PWM from current value
        
        @return: pwm value
        """
        
        self.speed_lock.acquire()
        self.speed["current"] = self.speed["target"] 
        self.speed_lock.release()
        
        stop_pwm, start_pwm, max_pwm = speed["range_pwm"]
        value = self.speed["current"]
        
        # If the target speed is negative, we consider that it is 0
        if value > 0:
            pwm_val = (max_pwm - start_pwm) * speed["current"] + start_pwm
        else:
            pwm_val = start_pwm
        return pwm_val
        
    
    def compute_direction(self):
        """
        Set the current value with the target.
        Compute PWM from current value
        
        @return: pwm value
        """
        self.dir_lock.acquire()
        self.direction["current"] = self.direction["target"] 
        self.dir_lock.release()
                        
        max_left_pwm, straight_pwm, max_right_pwm = self.direction["range_pwm"]
        value = self.direction["current"]
        
        # The PWM computation is not the same if the car turn to the right or to the left
        if value > 0:
            pwm_val = (max_right_pwm - straight_pwm)* value + straight_pwm
        else:
            pwm_val = (straight_pwm - max_left_pwm)* (1+value) + max_left_pwm
        return pwm_val
                
    def set_speed(self, value):
        """
        Clip the value, then set the desired speed
        
        @param value: normalized speed with a float
        @return: cliped value
        """
        if value > 1:
            value = 1
        elif value < -1:
            value = -1
    
        self.speed_lock.acquire()
        self.speed["target"] = value
        self.speed_lock.release()
        
        return value
    
    def set_direction(self, value):
        """
        Clip the value, then set the desired direction
        
        @param value: normalized direction with a float
        @return: cliped value
        """
        if value > 1:
            value = 1
        elif value < -1:
            value = -1
    
        self.dir_lock.acquire()
        self.direction["target"] = value
        self.dir_lock.release()
        
        return value
        
    def configure(self):
        """
        A quick function to visualize the effect of a precise PWM value
        """
        print("Pwm direction")
        pwm = self.direction["range_pwm"][1]
        while True:
            c = input()
            if "q" in c:
                pwm -= 5
            elif "d" in c:
                pwm += 5
            elif "s" in c:
                break
            print(pwm)
            self.pwm.set_pwm(self.direction["pin"], 0, pwm)
        
        
        print("Pwm speed")
        pwm = self.speed["range_pwm"][1]
        while True:
            c = input()
            if "q" in c:
                pwm -= 5
            elif "d" in c:
                pwm += 5
            elif "s" in c:
                break
            print(pwm)
            self.pwm.set_pwm(self.speed["pin"], 0, pwm)


class Car(Chassis):
    """
    Add an inertia term to prevent effects of outliers with the prediction.
    
    The car shouldn't make sudden changes of speed and direction.
    Sudden changes create chao and the car could not be controled anymore.
    Moreover, we try to protect the car and the components
    
    If the new value is close to the last one, we can change it.
    But if they are completely differents, the value applied is a mix between the 2.
    """
    def __init__(self):
        super().__init__()
        
        self.speed = {
            "range_pwm": (390, 407, 414),
            "current": 0,
            "target":  0,
            "pin": 5,
            "inertia": 0.8,
            
        }
        
        self.direction = {
            "range_pwm": (315, 410, 530),
            "current": 0,
            "target":  0,
            "pin": 10,
            "inertia": 0.7,
            
        }
    
    def compute_speed(self):
        """
        Set the current value with the target.
        Then compute PWM from current value
        
        @return: pwm value
        """
        self.speed_lock.release()
        self.speed["current"] = self._compute_offset(
                self.speed["target"],
                self.speed["current"],
                self.speed["inertia"]
        )
        self.speed_lock.release()
        
        stop_pwm, start_pwm, max_pwm = self.speed["range_pwm"]
        value = self.speed["current"]
        if value > 0:
            pwm_val = (max_pwm - start_pwm)* value + start_pwm
        else:
            pwm_val = start_pwm
        return pwm_val
    
    def compute_direction(self):
        """
        Set the current value with the target.
        Then compute PWM from current value
        
        @return: pwm value
        """
        self.dir_lock.acquire()
        self.direction["current"] = self._compute_offset(
                    self.direction["target"],
                    self.direction["current"],
                    self.direction["inertia"]
            )
        self.dir_lock.release()
        
        value = self.direction["current"]
        max_left_pwm, straight_pwm, max_right_pwm = self.direction["range_pwm"]
        if value > 0:
            pwm_val = (max_right_pwm - straight_pwm)* value + straight_pwm
        else:
            pwm_val = (straight_pwm - max_left_pwm)* (1+value) + max_left_pwm
        return pwm_val
    
    def _compute_offset(self, target, current, inertia):
        """
        The distance between the desired value and the current value is passed in the log function.
        For long distances between target and current, the change in value will be smoothed.
        
        @param target: the desired value to apply 
        @param current: the actual value
        @param intertia: float between 0 and 1, the larger it is, the smaller the change will be
        @return: the modified value
        """
        # Stop when the target is already achieved
        if current == target:
            return current       
        elif current > target:
            ratio = -1
        else:
            ratio = 1
        
        # Magic calculation
        offset = log(1.1+abs(target - current)) * (1 - inertia)/2
            
        # Avoid exceeding limit values
        if current > target:
            offset *= -1
            if current + offset < target:
                new = target
            else:
                new = current + offset
        elif current < target:
            if current + offset > target:
                new = target
            else:
                new = current + offset
        
        return new


class F1(Car):
    """
    Just disable the clipping for speed value. The problem is :
     * The car could brake too hard and stop at low speed
     * The car could slow down too slowly at high speed because of car inertia
    
    To prenvent this behaviour, we add high speed trace.
    If the high speed trace is 0, the clipping for lower speed value is enabled
    In any other cases, no clipping.
    
    Many magic numbers in compute_speed method, they were obtained empirically.
    """
    def __init__(self):
        super().__init__()
         
        self.speed = {
            "range_pwm": (375, 409, 413), # if battery is low 375 410 417
            "current": 0,
            "target":  0,
            "pin": 5,
            
        }
        
        self.direction = {
            "range_pwm": (315, 410, 530),
            "current": 0,
            "target":  0,
            "pin": 15,
            "inertia": 0.7,
            
        }
    
    def compute_speed(self):
        """
        Set the current value with the target.
        Then compute PWM from current value
        
        @return: pwm value
        """
        
        self.speed_lock.acquire()
        speed = self.speed
        
        # The case of no clipping
        if speed["target"] < 0 and self.high_speed_trace == 0:
            speed["current"] = 0
        # No clipping
        else:
            # For logs
            if speed["target"] < 0:
                print("BREAK !")
            speed["current"] = speed["target"]
        self.speed = speed
        self.speed_lock.release()
        
        # When the car accelerates quickly is the only case
        # where the trace is filling 
        if speed["current"] > 0.45:
            self.high_speed_trace += 0.4
        elif speed["current"] < 0: 
            self.high_speed_trace -= 0.1
        else:
            self.high_speed_trace -= 0.02
            
        # Clip the high_speed_trace to prevent extreme value
        # Simulating when the car reachs maximum or minimum speed
        if self.high_speed_trace < 0:
            self.high_speed_trace = 0
        elif self.high_speed_trace > 1.2:
            self.high_speed_trace = 1.2
        
        stop_pwm, start_pwm, max_pwm = speed["range_pwm"]
        if speed["current"] >= 0:
            pwm_val = (max_pwm - start_pwm)* speed["current"] + start_pwm
        else:
            pwm_val = stop_pwm
        return pwm_val
        
if __name__ == "__main__":
    car = Car().start()
    while True:
        car.set_direction(-1)
        sleep(5)
        car.set_direction(1)
        sleep(5)
