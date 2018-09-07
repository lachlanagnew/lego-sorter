import numpy as np
import cv2
import os
import sys
import time
import picamera
import picamera.array
import argparse
import RPi.GPIO as GPIO
import asyncio
import concurrent.futures
import firebase_admin
from firebase_admin import db
from firebase_admin import credentials

#GPIO INIT
servoPIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(servoPIN, GPIO.OUT)

p = GPIO.PWM(servoPIN, 50) # GPIO 17 for PWM with 50H
p.start(7.5) # Initialization

#CONSTANT
COLOR_TEXT={'R':0,'O':1,'Y':2,'G':3,'B':4}
COLORS=[[[120,160,0],[140,255,255]], [[101,170,0],[116,255,255]], [[85,150,0],[95,255,255]], [[50,180,50],[75,255,255]], [[10,190,90],[19,255,255]]]

#COMAND LINE ARGUMENTS
ap = argparse.ArgumentParser()

ap.add_argument("-s", "--showcamera", type=int, default=0,
	help="whether or not the Raspberry Pi camera should be displayed")
ap.add_argument("-f", "--framerate", type=int, default=30,
        help="the framerate that the camera gets updated")
ap.add_argument("-r", "--resolution", type=int, default=480,
        help="resolution of camera")
ap.add_argument("-c", "--colour", type=int, default=0,
        help="color to sort out (R, O, Y, G, B)")
args = vars(ap.parse_args())

#Globals
showcamera = args["showcamera"]
framerate = args["framerate"]
resolution = [int(args["resolution"]/3*4), int(args["resolution"])]
range = COLORS[args["colour"]]

cred = credentials.Certificate('firebase-adminsdk.json')
# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://lego-sorter.firebaseio.com/'
})
executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

db_data = {'motor':0,'color':'R'}


#FUNCTIONS
async def get_data():
    while True:
        ref = db.reference('sorter')
        global db_data
        global range
        db_data = await asyncio.get_event_loop().run_in_executor(executor, ref.get)
        range = COLORS[db_data['color']]
        await asyncio.sleep(0.1)

def moveServo():
    p.ChangeDutyCycle(2) # turn towards 180 degree
    time.sleep(0.6) # sleep 1 second
    p.ChangeDutyCycle(5) # turn towards 0 degree

def region_of_interest(img, vertices):
    mask = np.zeros_like(img)

    if len(img.shape) > 2:
        channel_count = img.shape[2]
        ignore_mask_color = (255,) * channel_count
    else:
        ignore_mask_color = 255

    cv2.fillPoly(mask, vertices, ignore_mask_color)

    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

def objectFound():
    moveServo()
    print("Found Object")

def mask_image_from_colour(image, lower, upper):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.GaussianBlur(hsv, (11, 11), 0)
    mask = cv2.inRange(mask, lower, upper)
    res = cv2.bitwise_and(hsv, hsv, mask=mask)
    res = cv2.cvtColor(cv2.cvtColor(res, cv2.COLOR_HSV2BGR), cv2.COLOR_BGR2GRAY)
    res = cv2.erode(res, None, iterations=2)
    res = cv2.dilate(res, None, iterations=5)
    return res

def draw_contours(image, masked):
    newImage = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    _ , contours, _ = cv2.findContours(masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(newImage, contours, -1, (255, 255, 0), 1)
    for cnt in contours:
        M = cv2.moments(cnt)
        (x,y),radius = cv2.minEnclosingCircle(cnt)
        if(radius > 10):
            #cv2.circle(newImage,center,radius,(0,255,0),2)
            objectFound()
            return newImage
    return newImage

def processed_image(image):
    global range
    lower_colour = np.array(range[0])
    upper_colour = np.array(range[1])
    masked = mask_image_from_colour(image, lower_colour, upper_colour)
    return draw_contours(image, masked)


async def main():
    print('Starting')
    future = asyncio.ensure_future(get_data())
    with picamera.PiCamera() as camera:
        with picamera.array.PiRGBArray(camera) as output:
            global resolution
            global framerate
            camera.resolution = (resolution[0], resolution[1]) #(192, 144)
            camera.framerate = framerate
            while(1):
                camera.capture(output, 'rgb')
                try:
                    global db_data
                    global showcamera
                    global img
                    print(db_data)
                    img = output.array
                    output.truncate(0)
                    result = processed_image(img)
                    await asyncio.sleep(0.05)
                    if (showcamera == True):
                        cv2.imshow('img',result)
                    if 0xFF & cv2.waitKey(5) == 27:
                        break
                except KeyboardInterrupt:
                    pass
                    print ('KB interrupted')
                    print ('Process Aborted!')
                    break
                except Exception as e:
                    exc_type, exc_obj, tb = sys.exc_info()
                    lineno = tb.tb_lineno
                    print ('Error : ' + str(e) + " @ line " + str(lineno))
                finally:
                    pass
    p.stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()
    print ('Aborted')
    future.cancel()
if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
