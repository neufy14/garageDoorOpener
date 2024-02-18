import sys
import cv2 
import imutils
import config
import threading
import numpy as np
import time
import datetime
import os
import json
from easyocr import Reader
from JetsonYolov5.yoloDet import YoloTRT
import RPi.GPIO as GPIO
from collections import deque


class garageDoorCam:
    def __init__(self):
        print("start")
        videoBuffer = deque()
        # self.videoFile = 0
        self.readyForNewFrame = False
        self.runProgram = True
        self.saveBuffer = False
        self.foundPlatesTS = []
        frameNumber = 0
        # color = (255, 0, 0)
        thickness = 2
        successIdentification = 0
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(config.setDoorPin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(config.readDoorPin, GPIO.IN)
        language = ['en']
        reader = Reader(language)

        np.random.seed(42)
        print("getting model")
        model = YoloTRT(library=config.libLoc, engine=config.engineLoc, conf=config.confidenceThresh, yolo_ver="v5")
        COLORS = np.random.randint(0, 255, size=(len(model.categories), 3),
                                   dtype="uint8")
        print("model loaded")
        print("model names = ", model.categories)
        if config.useLiveVideo:
            # start camera thread to get live video feed
            print("starting video thread")
            videoThread = threading.Thread(target=self.cameraThread, args=(config.videoFile,))
            videoThread.start()
            print("video thread started")
        doorStatusThread = threading.Thread(target=self.checkDoor)
        doorStatusThread.start()
        while self.runProgram:
            plateFound = False
            # print("self.readyForNewFrame = ", self.readyForNewFrame)
            if self.readyForNewFrame and self.doorClosed:
                currentFrame = self.frame
                blankImage = currentFrame.copy()
                frameNumber += 1
                self.readyForNewFrame = False
                if not config.useLiveVideo:
                    self.ret, currentFrame = self.capture.read()
                    if self.ret == False:
                        break
                    self.readyForNewFrame = True
                print("about to run model")
                #print("currentFrame = ", currentFrame)
                if currentFrame is None:
                    print("frame is empty")
                else:
                    #videoBuffer.append(currentFrame)
                    #if len(videoBuffer) > config.videoBufferLength:
                    #    print("delete frame")
                    #    videoBuffer.popleft()
                    results, t = model.Inference(currentFrame)
                    print("results = ", results)
                    licenseNum = 0
                    for output in results:
                        print("output[box] = ", output["box"])
                        upperleft = (int(output["box"][0]), int(output["box"][1]))
                        buttomRight = (int(output["box"][2]), int(output["box"][3]))
                        if output["class"] in config.validSkus and output["conf"] > config.modelConfidence:
                            # definitions of variables for output image
                            modelName = output["class"] + ": " + str(output["conf"])
                            color = (int(COLORS[model.categories.index(output["class"])][0]), int(COLORS[model.categories.index(output["class"])][1]), int(COLORS[model.categories.index(output["class"])][2]))
                        
                            # Create a cropped image that shows just the bounding box out of NN then look at just the bottom 1/4 to find the license place
                            yStart = (output["box"][1] + output["box"][3]) / 4
                            croppedImage = blankImage[int(yStart):int(output["box"][3]), int(output["box"][0]):int(output["box"][2]), :]
                            (tlx, tly, cropWidth, cropHeight) = self.lookForLicensePlate(croppedImage)
                            print("found a license plate")
                            corners = [(tly-config.erodeAmount), (tly+cropWidth+config.erodeAmount), (tlx-config.erodeAmount), (tlx+cropWidth+config.erodeAmount)]
                            for i in range(len(corners)):
                                if corners[i] < 0:
                                    corners[i] = 0
                                if i < 2 and corners[i] > abs(int(yStart) - int(output["box"][3])):
                                    corners[i] = len(croppedImage)
                                elif i > 1 and corners[i] > abs(int(output["box"][0] - int(output["box"][2]))):
                                    corners[i] = len(croppedImage[0])
                            licenseImage = croppedImage[corners[0]:corners[1], corners[2]:corners[3]]

                            #draw bounding boxes and text on original image
                            self.frame = cv2.rectangle(self.frame, upperleft, buttomRight, color, thickness)
                            cv2.putText(self.frame, modelName, (upperleft[0], upperleft[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            print("writing image")
                            cv2.imwrite("testImages/licensePlate" + str(licenseNum) + ".jpeg", licenseImage)
                            # read license plate
                            licenseNum += 1
                            print("getting text")
                            imageText = reader.readtext(licenseImage)
                            print("text in image = ", imageText)
                            for (bbox, text, probability) in imageText:
                                plateFound = False
                                for char in config.chars2Ignore:
                                    text = text.replace(char, "")
                                # for validPlate in config.validPlates:
                                for validPlate in self.getValidPlates():
                                    if validPlate.casefold() in text.casefold():
                                        textColor = (50, 255, 0)
                                        plateFound = True
                                        successIdentification += 1
                                        print("license plate correctly identified, about to open the door")
                                        GPIO.output(config.setDoorPin, GPIO.HIGH)
                                        print("pin set high, sleep for 2 seconds")
                                        print("Start : %s" % time.ctime())
                                        time.sleep(2)
                                        print("End : %s" % time.ctime())
                                        print("pin set back low")
                                        GPIO.output(config.setDoorPin, GPIO.LOW)
                                        currentTime = datetime.datetime.now()
                                        cv2.imwrite("foundPlateImages/" + str(currentTime) + ".jpg", currentFrame)
                                        self.foundPlatesTS.append(currentTime)
                                        if len(self.foundPlatesTS) > config.maxStoredImages:
                                            image2Delete = self.foundPlatesTS.pop(0)
                                            os.remove("foundPlateImages/" + str(image2Delete) + ".jpg")
                                        self.checkSavedImageAge()
                                        self.saveBuffer = True
                                        break
                                    elif validPlate not in text and not plateFound:
                                        textColor = (0, 0, 255)
                                if plateFound:
                                    print("breaking out because license found")
                                    break
                        if plateFound:
                            break
                    cv2.imwrite("testImages/test.jpeg", currentFrame)
                    cv2.imwrite("testImages/blankTest.jpeg", blankImage)
        videoThread.join()
        doorStatusThread.join()


    def getValidPlates(self):
        validPlate = []
        doorDataJson = open('doorData.json')
        data = json.load(doorDataJson)
        for i in data['validLicensePlates']:
            validPlate.append(data['validLicensePlates'][i])
        doorDataJson.close()
        # print('validPlate = ', validPlate)
        return validPlate

    def checkSavedImageAge(self):
        currentTS = datetime.datetime.now()
        numDelete = 0
        for timestamp in self.foundPlatesTS:
            oldTimePlusKeepTime = timestamp + datetime.timedelta(days=config.deleteAfterTime)
            if oldTimePlusKeepTime < currentTS:
                numDelete += 1
            elif oldTimePlusKeepTime > currentTS:
                break
        for i in range(0, numDelete):
            image2Delete = self.foundPlatesTS.pop(0)
            os.remove("foundPlateImages/" + str(image2Delete) + ".jpg")

    
    def checkDoor(self):
        while self.runProgram:
            if GPIO.input(config.readDoorPin) == GPIO.HIGH:
                #Garage Door is closed
                self.doorClosed = True
                doorStatus = {"doorStatus": "Closed"}
                with open("doorData.json", "r+") as outfile:
                    allData = json.load(outfile)
                    # print("allData json = ", allData)
                    outfile.seek(0)
                    allData["doorStatus"] = "Closed"
                    json.dump(allData, outfile)
                    outfile.truncate()
                print("the door is closed")
            else:
                self.doorClosed = False
                doorStatus = {"doorStatus": "Open"}
                with open("doorData.json", "r+") as outfile:
                    allData = json.load(outfile)
                    # print("allData json = ", allData)
                    outfile.seek(0)
                    allData["doorStatus"] = "Open"
                    json.dump(allData, outfile)
                    outfile.truncate()
                print("the door is open")
            time.sleep(1)


    def lookForLicensePlate(self, carImage):
        if config.colorSpace == "RGB":
            grayCarImage = cv2.cvtColor(carImage, cv2.COLOR_BGR2GRAY)
            carEdgeImage = cv2.Canny(grayCarImage, config.lowerCanny, config.upperCanny, apertureSize=config.aperture_size)
            contours, hierarchy = cv2.findContours(carEdgeImage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        elif config.colorSpace == "HSV":
            # hsv approach only looking at H channel
            hsvCarImg = cv2.cvtColor(carImage, cv2.COLOR_BGR2HSV)
            hsvCarImg[:, :, 0] = 0
            hsvCarImg[:, :, 2] = 0
            hsvGausBlur = cv2.GaussianBlur(hsvCarImg, (5, 5), 0)
            hsvCarEdgeImage = cv2.Canny(hsvGausBlur, config.lowerCanny, config.upperCanny, apertureSize=config.aperture_size)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            dilatedEdgeImage = cv2.dilate(hsvCarEdgeImage, kernel)
            contours, hsvHierarchy = cv2.findContours(dilatedEdgeImage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)


        # boundingBoxArea = [None] * len(contours)
        minAreaDif = float('inf')
        minAreaDifIdx = -1
        count = 0
        imageCopy = carImage.copy()
        for contour in contours:
            # imageCopy = carImage.copy()
            boundRect = cv2.boundingRect(contour)
            ((x, y), (width, height), angle) = cv2.minAreaRect(contour)
            # print("x = ", x)
            # print("y = ", y)
            # print("width = ", width)
            # print("height = ", height)
            # print("angle = ", angle)
            boundingBoxArea = width * height
            area = cv2.contourArea(contour)
            # approxArea = cv2.contourArea(approx)
            # print("area = ", area)
            # print("approxArea = ", approxArea)
            if area > config.contourMinArea:
                print("License Contour Area = ", area)
                areaDif = abs(boundingBoxArea - area)
                # print("new contour = ", count)
                # print("boundingBoxArea = ", boundingBoxArea)
                # print("areaDif = ", areaDif)
                if areaDif < minAreaDif:
                    minAreaDif = areaDif
                    minAreaDifIdx = count
                    # print("new min")
                # upcomment this imshow lines and waitKey line for useful debug images
                # cv2.drawContours(imageCopy, hsvContours, count, (0, 255, 255), 2)
                # cv2.rectangle(imageCopy, (boundRect[0], boundRect[1]), (boundRect[0]+boundRect[2], boundRect[1]+boundRect[3]), (255, 0, 0), 2)
                # cv2.drawContours(imageCopy, approx, -1, (0, 255, 0), 2)
                # cv2.drawContours(hsvCarImg, hsvContours, count, (0, 255, 0), 2)
                # cv2.imshow("hsv image", hsvGausBlur)
                # cv2.imshow("edge image", hsvCarEdgeImage)
                # cv2.imshow("diolated edge image", dilatedEdgeImage)
                # cv2.imshow("car image with contour", imageCopy)
                # cv2.waitKey(0)
                # cv2.destroyWindow("car image with contour")
            count += 1
        finalBox = cv2.boundingRect(contours[minAreaDifIdx])
        return finalBox

    def cameraThread(self, filename):
        #self.videoBuffer = deque()
        self.bufferReadyForFrame = True
        self.saveVideoComplete = False
        self.bufferActive = False
        self.capture = cv2.VideoCapture(filename)
        self.ret, self.frame = self.capture.read()
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter(config.saveVideoFileName, fourcc, 20.0, (1920, 1080))
        self.bufferOut = cv2.VideoWriter("bufferVideo.avi", fourcc, 20.0, (1920, 1080))
        while self.ret:
            # self.capture = cv2.VideoCapture(self.videoFile)
            self.ret, self.frame = self.capture.read()
            #self.readyForNewFrame = True
            #self.videoBuffer.appendleft(self.frame)
            #if self.bufferReadyForFrame:
            #    self.bufferActive = True
            #    self.bufferReadyForFrame = False
            #    bufferThread = threading.Thread(target=self.add2Buffer, args=())
            #    bufferThread.start()
            #elif self.bufferActive == False and self.bufferReadyForFrame == False:
            #    bufferThread.join()
            #    self.bufferReadyForFrame = True
            if config.saveVideo:
                self.out.write(self.frame)
            #if self.saveBuffer:
            #    self.saveBuffer = False
            #    print("saving buffer video")
            #    videoWriteThread = threading.Thread(target=self.writeVideo, args=())
            #    videoWriteThread.start()
                #for frames in videoBuffer:
                #    self.bufferOut.write(frames)
                #self.bufferOut.release()
                #self.bufferOut = cv2.VideoWriter("bufferVideo.avi", fourcc, 20.0, (1920, 1080))
                #self.saveBuffer = False
            #if self.saveVideoComplete:
            #    videoWriteThread.join()
            #    self.saveVideoComplete = False
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            if not self.ret:
                print("Camera Disconected, trying to reconnect")
                self.capture.release()
                self.capture = cv2.VideoCapture(filename)
                self.ret, self.frame = self.capture.read()
            self.readyForNewFrame = True

            if 0xFF == ord('q'):
                self.capture.release()
                self.out.release()
                #self.bufferOut.release()
                self.runProgram = False
                break
        print("video thread exit")

    def writeVideo(self):
        for i in range(0, len(self.videoBuffer)):
            self.bufferOut.write(self.videoBuffer[i].popleft())
        self.bufferOut.release()
        self.bufferOut = cv2.VideoWriter("bufferVideo.avi", fourcc, 20.0, (1920, 1080))
        self.saveVideoComplete = True

    def add2Buffer(self):
        self.videoBuffer.append(self.frame)
        #self.bufferReadyForFrame = True
        self.bufferActive = False


garageDoorCam()
