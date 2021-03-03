from Adafruit_PCA9685 import PCA9685

"""
Use this script to stop the car.
"""

pwm = PCA9685()
pwm.set_pwm_freq(60)

pwm.set_pwm(15, 0, 410) # dir
pwm.set_pwm(5, 0, 390) # speed
