import RPi.GPIO as GPIO
import config
import time

GPIO.setmode(GPIO.BOARD)
GPIO.setup(config.setDoorPin, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(config.setDoorPin, GPIO.HIGH)
time.sleep(2)
GPIO.output(config.setDoorPin, GPIO.LOW)
print('hello world')
