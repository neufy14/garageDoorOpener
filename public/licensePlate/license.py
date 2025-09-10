import sys
import cv2 
# import imutils
import config
import threading
import numpy as np
import time
import datetime
import os
import json
import csv
import logging
import psutil
import put2S3
# import cameraMode
import uuid
# from cameraMode import adjustCamera
from databaseScript import add2Database
from easyocr import Reader
from JetsonYolov5.yoloDet import YoloTRT
import RPi.GPIO as GPIO
from collections import deque
from logging.handlers import TimedRotatingFileHandler


class garageDoorCam:
    def __init__(self):
        print("start")
        # Create and configure logger
        logging.basicConfig(filename="newfile.log",
                            format='%(asctime)s %(message)s',
                            filemode='a')
        # Creating an object
        self.logger = logging.getLogger()
        
        # Setting the threshold of logger to DEBUG
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("The start of the log")

        # Configure the TimedRotatingFileHandler
        handler = TimedRotatingFileHandler('newfile.log', when='midnight', interval=1, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

        process = psutil.Process()

        # videoBuffer = deque()
        # self.videoFile = 0
        self.readyForNewFrame = False
        self.runProgram = True
        self.runCheckDoor = True
        self.stopCheckDoorThread = False
        self.programRunning = True
        self.saveBuffer = False
        self.doorClosed = True
        self.scheduledActionsExist = False
        self.scheduledAction = []
        self.foundPlatesTS = []
        self.logDoorOpen = False
        # localAdjustCamera = adjustCamera()

        frameNumber = 0
        # color = (255, 0, 0)
        thickness = 2
        successIdentification = 0
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(config.setDoorPin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(config.readDoorPin, GPIO.IN)
        
        if GPIO.input(config.readDoorPin) == GPIO.HIGH:
            # The door is currently closed
            self.setDoorInfo(False)
            # GPIO.add_event_detect(config.readDoorPin, GPIO.FALLING, callback=lambda channel: self.setDoorInfo(False), bouncetime=200)
            self.doorClosed = True
            self.logDoorOpen = False
        else:
            # The door is currently open
            self.setDoorInfo(True)
            # GPIO.add_event_detect(config.readDoorPin, GPIO.RISING, callback=lambda channel: self.setDoorInfo(True), bouncetime=200)
            self.doorClosed = False
            self.logDoorOpen = True
        

        language = ['en']
        reader = Reader(language, gpu=True)
        
        np.random.seed(42)
        print("getting model")
        model = YoloTRT(library=config.libLoc, engine=config.engineLoc, conf=config.confidenceThresh, yolo_ver="v5")
        COLORS = np.random.randint(0, 255, size=(len(model.categories), 3),
                                   dtype="uint8")
        print("model loaded")
        print("model names = ", model.categories)
        if config.useLiveVideo:
            # start camera thread to get live video feed
            self.logger.debug("starting video thread")
            videoThread = threading.Thread(target=self.cameraThread, args=(config.videoFile,))
            videoThread.start()
            print("video thread started")
        # monitorCameraModeThread = threading.Thread(target=self.runCameraMonitor, args=(localAdjustCamera,))
        # monitorCameraModeThread.start()

        # ----------------------checkDoorThread--------------------------------------
        # doorStatusThread = threading.Thread(target=self.checkDoor)
        # doorStatusThread.start()
        
        self.logger.debug("about to enter main loop")
        while self.runProgram:
            plateFound = False
            # if self.stopCheckDoorThread:
            #     doorStatusThread.join()
            #     self.logger.debug("stopping check door thread to change camera")
            #     if cameraMode.adjustCamera.isDaytime:
            #         modeSend = "day"
            #     else:
            #         modeSend = 'night'
            #     self.logger.debug("about to run switch mode from main program")
            #     localAdjustCamera.switchMode(modeSend)
            #     self.logger.debug("past switch mode in main program")
            #     # while cameraMode.adjustCamera.settingsChange:
            #     #     time.sleep(1)
            #     doorStatusThread = threading.Thread(target=self.checkDoor)
            #     doorStatusThread.start()
            #     self.stopCheckDoorThread = False
            
            if self.readyForNewFrame and self.doorClosed and (self.frame is not None) and self.programRunning:
                self.logDoorOpen = True
                self.logger.debug("Memory usage: %s MB", (process.memory_info().rss / (1024 * 1024)))
                currentFrame = self.frame
                self.confirmDoor()
                frameNumber += 1
                self.readyForNewFrame = False
                if not config.useLiveVideo:
                    self.ret, currentFrame = self.capture.read()
                    if self.ret == False:
                        break
                    self.readyForNewFrame = True
                print("about to run model")
                self.logger.debug("New frame grabbed, running model")
                #print("currentFrame = ", currentFrame)
                if currentFrame is None:
                    print("frame is empty")
                    self.logger.debug("Frame was empty")
                else:
                    blankImage = currentFrame.copy()
                    #videoBuffer.append(currentFrame)
                    #if len(videoBuffer) > config.videoBufferLength:
                    #    print("delete frame")
                    #    videoBuffer.popleft()
                    try:
                        results, t = model.Inference(currentFrame)
                    except Exception as e:
                        self.logger.debug("Error running inference: %s", e)
                        # print(f"Error running inference: {e}")
                    else:
                        # print("results = ", results)
                        licenseNum = 0
                        for output in results:
                            # print("output[box] = ", output["box"])
                            upperleft = (int(output["box"][0]), int(output["box"][1]))
                            buttomRight = (int(output["box"][2]), int(output["box"][3]))
                            if output["class"] in config.validSkus and output["conf"] > config.modelConfidence:
                                self.logger.debug("Found a car, looking for a license plate, iteration %s", licenseNum)
                                # definitions of variables for output image
                                modelName = output["class"] + ": " + str(output["conf"])
                                color = (int(COLORS[model.categories.index(output["class"])][0]), int(COLORS[model.categories.index(output["class"])][1]), int(COLORS[model.categories.index(output["class"])][2]))
                            
                                # Create a cropped image that shows just the bounding box out of NN then look at just the bottom 1/4 to find the license place
                                yStart = (output["box"][1] + output["box"][3]) / 4
                                croppedImage = blankImage[int(yStart):int(output["box"][3]), int(output["box"][0]):int(output["box"][2]), :]

                                (tlx, tly, cropWidth, cropHeight) = self.lookForLicensePlateGpu(croppedImage)
                                if cropWidth > 30 and cropHeight > 15 and cropWidth < 500 and cropHeight < 300:
                                    self.logger.debug("Found a license plate %s X %s", cropWidth, cropHeight)
                                    # print("found a license plate: ", cropWidth, " x ", cropHeight)
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
                                    self.logger.debug("Writing images")
                                    if croppedImage is None:
                                        self.logger.debug("current frame is empty")
                                    else:
                                        # cv2.rectangle(croppedImage, (tlx, tly), (tlx+cropWidth, tly+cropHeight), (255, 0, 0), 2)
                                        # cv2.imwrite("testImages/contourImages/contourImages" + str(count) + ".jpg", imageCopy)
                                        cv2.imwrite("testImages/fullImage" + str(licenseNum) + ".jpeg", croppedImage)
                                    if licenseImage is None:
                                        self.logger.debug("license image is empty")
                                    else:
                                        cv2.imwrite("testImages/licensePlate" + str(licenseNum) + ".jpeg", licenseImage)
                                        licenseImageGray = cv2.cvtColor(licenseImage, cv2.COLOR_BGR2GRAY)
                                    # read license plate
                                    licenseNum += 1
                                    self.logger.debug("Getting Text")
                                    try:
                                        imageText = reader.readtext(licenseImageGray)
                                    except Exception as e:
                                        self.logger.debug("Error reading text: %s", e)
                                    else:
                                        self.logger.debug("Text found in image: %s", imageText)
                                        plateFound = self.evaluateText(imageText, currentFrame)
                                        if not plateFound:
                                            currentTime = datetime.datetime.now()
                                            wrongPlateFilename = "foundPlateImages/wrongPlateImages/" + str(currentTime).replace(" ", "_").replace(":", "-") + ".jpg"
                                            cv2.imwrite(wrongPlateFilename, licenseImage)
                                else:
                                    self.logger.debug("Found a license plate but it is too small: %s X %s", cropWidth, cropHeight)
                            # else:
                            #     self.logger.debug("No car found")
                            if plateFound:
                                break
                    cv2.imwrite("testImages/test.jpeg", currentFrame)
                    cv2.imwrite("testImages/blankTest.jpeg", blankImage)
                    del blankImage
                    self.logger.debug("Loop complete, getting new frame")
            elif not self.doorClosed:
                # The door is open
                self.confirmDoor()
                if self.logDoorOpen:
                    self.logger.debug("The door is open so we are not processing images")
                    self.logDoorOpen = False
            elif not self.programRunning:
                self.getValidPlates()
        videoThread.join()
        doorStatusThread.join()
        monitorCameraModeThread.join()

    def confirmDoor(self):
        if self.doorClosed and GPIO.input(config.readDoorPin) == GPIO.LOW:
            # Door info incorrectly set, perform correction action
            self.logger.debug("The door info was showing door closed, but input pin shows open. Default to sensor input")
            self.setDoorInfo(True)
            self.doorClosed = False
        elif not self.doorClosed and GPIO.input(config.readDoorPin) == GPIO.HIGH:
            # Door info incorrectly set, perform correction action
            self.logger.debug("The door info was showing door open, but input pin shows closed. Default to sensor input")
            self.setDoorInfo(False)
            self.doorClosed = True

    def evaluateText(self, foundText, currentFrame):
        plateFound = False
        for (bbox, text, probability) in foundText:
            plateFound = False
            for char in config.chars2Ignore:
                text = text.replace(char, "")
            # for validPlate in config.validPlates:
            for index, validPlate in enumerate(self.getValidPlates()[0]):
                self.confirmDoor()
                if validPlate.casefold() in text.casefold() and self.doorClosed and self.programRunning:
                    textColor = (50, 255, 0)
                    plateFound = True
                    print("license plate correctly identified, about to open the door")
                    # GPIO.output(config.setDoorPin, GPIO.HIGH)
                    # print("pin set high, sleep for 2 seconds")
                    # print("Start : %s" % time.ctime())
                    # time.sleep(2)
                    # print("End : %s" % time.ctime())
                    # print("pin set back low")
                    # GPIO.output(config.setDoorPin, GPIO.LOW)
                    self.triggerDoor()
                    currentTime = datetime.datetime.now()
                    data = (index, validPlate, currentTime)
                    self.logger.debug("Index to send to database: %s", str(index))
                    self.logger.debug("ValidPlate to send to database: %s", str(validPlate))
                    self.logger.debug("Timestamp to send to database: %s", str(currentTime))
                    add2Database(data)
                    self.logger.debug("Added to the database")
                    
                    putFilename = "foundPlateImages/" + str(currentTime).replace(" ", "_").replace(":", "-") + ".jpg"
                    placeFilename = "public/foundPlateImages/" + str(currentTime).replace(" ", "_").replace(":", "-") + ".jpeg"
                    cv2.imwrite(putFilename, currentFrame)
                    put2S3.put2S3(putFilename, placeFilename)

                    # Generate a random UUID (version 4)
                    random_id = uuid.uuid4()
                    # Convert UUID to string
                    random_id_str = str(random_id)
                    uuidPutFilename = "plates/valid/" + random_id_str + ".jpg"
                    uuidPlaceFilename = "public/foundPlateImages/valid/" + random_id_str + ".jpeg"
                    cv2.imwrite(uuidPutFilename, currentFrame)
                    put2S3.put2S3(uuidPutFilename, uuidPlaceFilename)
                    validPlatesReturn = self.getValidPlates()
                    metadata = {
                        "filename": random_id_str,
                        "timestamp": str(currentTime),
                        "user": validPlatesReturn[1][index]
                    }
                    put2S3.sendMetaData(metadata)

                    self.checkCsv(index, validPlate, currentTime) 

                    # # old non working csv data management
                    # with open(config.foundPlatesFilename, mode='r') as file:
                    #     self.foundPlatesTS = list(csv.reader(file, delimiter=','))
                    #     # self.foundPlatesTS = list(json.load(file))
                    #     self.foundPlatesTS.append(currentTime)
                    #     if len(self.foundPlatesTS) > config.maxStoredImages:
                    #         image2Delete = self.foundPlatesTS.pop(0)
                    #         os.remove("foundPlateImages/" + str(image2Delete) + ".jpg")
                    #     # json.dump(self.foundPlatesTS, file, indent=4, sort_keys=True, default=str)
                    # with open(config.foundPlatesFilename, mode='w') as file:
                    #     write = csv.writer(file)
                    #     write.writerow(self.foundPlatesTS)
                    self.checkSavedImageAge()
                    self.saveBuffer = True
                    break
                elif validPlate not in text and not plateFound:
                    textColor = (0, 0, 255)
                    w = bbox[0][0] - bbox[2][0]
                    h = bbox[0][1] - bbox[2][1]
                    a = w * h
                    if a > config.plateArea and w > h:
                        self.logger.debug("Found a plate but it is not valid")
                                            # Generate a random UUID (version 4)
                        random_id = uuid.uuid4()
                        # Convert UUID to string
                        random_id_str = str(random_id)
                        uuidPutFilename = "plates/invalid/" + random_id_str + ".jpg"
                        cv2.imwrite(uuidPutFilename, currentFrame)
                elif validPlate in text and not self.doorClosed:
                    self.logger.debug("Found a plate but the door is already open")
                elif validPlate in text and not self.programRunning:
                    self.logger.debug("Found a plate but program running toggle off")
            if plateFound:
                # print("breaking out because license found")
                break
        return plateFound

    def triggerDoor(self):
        if not config.testMode:
            GPIO.output(config.setDoorPin, GPIO.LOW)
            # print("pin set high, sleep for 2 seconds")
            # print("Start : %s" % time.ctime())
            time.sleep(5)
            # print("End : %s" % time.ctime())
            # print("pin set back low")
            GPIO.output(config.setDoorPin, GPIO.HIGH)
        else:
            self.logger.debug("In test mode, not opening the door.")

    def checkCsv(self, idx, plate, time):
        csvData = self.openCsv()
        self.foundPlatesTS = []
        if len(csvData) == 0:
            data = [[idx, plate, time]]
            self.foundPlatesTS = data
            startCsv = True
        else:
            startCsv = False
            data = [idx, plate, time]
            for csvLine in csvData:
                self.foundPlatesTS.append(csvLine)
            self.foundPlatesTS.append(data)
        while len(self.foundPlatesTS) > config.maxStoredImages:
            image2Delete = self.foundPlatesTS.pop(0)
            self.logger.debug("Removing %s", str(image2Delete[2]))
            formatedImage = image2Delete[2].replace(" ", "_")
            formatedImage = formatedImage.replace(":","-")
            os.remove("foundPlateImages/" + str(formatedImage) + ".jpg")
        with open(config.foundPlatesFilename, mode='w', newline='') as file:
            write = csv.writer(file, delimiter=',')
            for plate in self.foundPlatesTS:
                write.writerow(plate)


    def openCsv(self):
        data = []
        with open(config.foundPlatesFilename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                data.append(row)
        return data

    def getValidPlates(self):
        validPlate = []
        userNames = []
        doorDataJson = open('doorData.json')
        data = json.load(doorDataJson)
        self.programRunning = data['runProgram']
        for i in data['validLicensePlates']:
            validPlate.append(data['validLicensePlates'][i])
            userNames.append(i)
        doorDataJson.close()
        # print('validPlate = ', validPlate)
        return validPlate, userNames

    def checkSavedImageAgeSave(self):
        currentTS = datetime.datetime.now()
        numDelete = 0
        format = '%Y-%m-%d %H:%M:%S.%f'
        with open(config.foundPlatesFilename, 'r') as file:
            self.foundPlatesTS = list(csv.reader(file, delimiter=","))
            for timestamp in self.foundPlatesTS:
                oldTimePlusKeepTime = datetime.datetime.strptime(timestamp[2], format) + datetime.timedelta(days=config.deleteAfterTime)
                if oldTimePlusKeepTime < currentTS:
                    numDelete += 1
                elif oldTimePlusKeepTime > currentTS:
                    break
            for i in range(0, numDelete):
                image2Delete = self.foundPlatesTS.pop(0)
                os.remove("foundPlateImages/" + str(image2Delete) + ".jpg")
        with open(config.foundPlatesFilename, mode='w', newline='') as file:
            write = csv.writer(file, delimiter=',')
            for plate in self.foundPlatesTS:
                write.writerow(plate)

    def checkSavedImageAge(self):
        currentTS = datetime.datetime.now()
        index2Delete = []
        numDelete = 0
        format = '%Y-%m-%d %H:%M:%S.%f'
        self.foundPlatesTS = self.openCsv()
        for timestamp in self.foundPlatesTS:
            oldTimePlusKeepTime = datetime.datetime.strptime(timestamp[2], format) + datetime.timedelta(days=config.deleteAfterTime)
            if oldTimePlusKeepTime < currentTS:
                numDelete += 1
                index2Delete.append(int(timestamp[0]))
        for i in range(0, numDelete):
            image2Delete = self.foundPlatesTS.pop(index2Delete[i])
            try:
                os.remove("foundPlateImages/" + str(image2Delete[2]) + ".jpg")
            except Exception as e:
                self.logger.debug("Error deleting old image")
        with open(config.foundPlatesFilename, mode='w', newline='') as file:
            write = csv.writer(file, delimiter=',')
            for plate in self.foundPlatesTS:
                write.writerow(plate)


    def setDoorInfo(self, doorOpen):
        self.logger.debug("setDoorInfo event triggered")
        getDoorDataFilename = "doorData.json"
        putDoorDataFilename = "public/doorData.json"
        GPIO.remove_event_detect(config.readDoorPin)

        if doorOpen:
            status = "Open"
            self.doorClosed = False
            self.logger.debug("The door is now open")
            # GPIO.add_event_detect(config.readDoorPin, GPIO.RISING, callback=lambda channel: self.setDoorInfo(False), bouncetime=200)
        else:
            status = "Closed"
            self.doorClosed = True
            self.logger.debug("The door is now closed")
            # GPIO.add_event_detect(config.readDoorPin, GPIO.FALLING, callback=lambda channel: self.setDoorInfo(True), bouncetime=200)
        try:
            with open("doorData.json", "r+") as outfile:
                allData = json.load(outfile)
                # print("allData json = ", allData)
                outfile.seek(0)
                allData["doorStatus"] = status
                json.dump(allData, outfile)
                outfile.truncate()
            # print("the door is open")
        except Exception as e:
            self.logger.debug("JSON decode error: %s", e)
        doorDataJson = open('doorData.json')
        data = json.load(doorDataJson)
        # if self.programRunning != data['runProgram']:
        #     self.programRunning = data['runProgram']
        #     if self.programRunning:
        #         self.logger.debug("The program is actively running")
        #     else:
        #         self.logger.debug("The program is stopped")
        doorDataJson.close()
        put2S3.put2S3(getDoorDataFilename, putDoorDataFilename)


    def checkDoor(self):
        self.logger.debug("starting check door thread")
        getDoorDataFilename = "doorData.json"
        putDoorDataFilename = "public/doorData.json"
        while self.runCheckDoor:
            updateS3 = False
            self.getSchedule()
            if GPIO.input(config.readDoorPin) == GPIO.HIGH:
                #Garage Door is closed
                self.logger.debug("The door is closed")
                self.doorClosed = True
                doorStatus = {"doorStatus": "Closed"}
                try:
                    with open("doorData.json", "r+") as outfile:
                        allData = json.load(outfile)
                        # print("allData json = ", allData)
                        outfile.seek(0)
                        if allData["doorStatus"] == "Open":
                            updateS3 = True
                        allData["doorStatus"] = "Closed"
                        json.dump(allData, outfile)
                        outfile.truncate()
                    # print("the door is closed")
                except Exception as e:
                    self.logger.debug("JSON decode error: %s", e)
            else:
                self.doorClosed = False
                doorStatus = {"doorStatus": "Open"}
                self.logger.debug("The door is open")
                try:
                    with open("doorData.json", "r+") as outfile:
                        allData = json.load(outfile)
                        # print("allData json = ", allData)
                        outfile.seek(0)
                        if allData["doorStatus"] == "Closed":
                            updateS3 = True
                        allData["doorStatus"] = "Open"
                        json.dump(allData, outfile)
                        outfile.truncate()
                    # print("the door is open")
                except Exception as e:
                    self.logger.debug("JSON decode error: %s", e)
            doorDataJson = open('doorData.json')
            data = json.load(doorDataJson)
            if self.programRunning != data['runProgram']:
                self.programRunning = data['runProgram']
                if self.programRunning:
                    self.logger.debug("The program is actively running")
                else:
                    self.logger.debug("The program is stopped")
            doorDataJson.close()
            if updateS3:
                put2S3.put2S3(getDoorDataFilename, putDoorDataFilename)
                updateS3 = False
            time.sleep(1)
        self.stopCheckDoorThread = True
        self.logger.debug("ending check door thread")


    def getSchedule(self):
        scheduledActionsExist = False
        scheduledAction = []
        try:
            with open("doorData.json", "r+") as outfile:
                allData = json.load(outfile)
                # print("allData = ", allData)
                schedules = allData["scheduledActions"]
                doorStatus = allData["doorStatus"]
                # print("schedules = ", schedules)
                for schedule in schedules:
                    if schedule["runProgramToggleInput"]:
                        scheduledActionsExist = True
                        action = [datetime.datetime.strptime(schedule["timeInput"], "%H:%M"), schedule["openclosebuttonInput"]]
                        scheduledAction.append(action)
            sortedSchedule = sorted(scheduledAction)
            # print("sortedSchedule = ", sortedSchedule)
            now = datetime.datetime.now()
            index = 0
            while True:
                # print("len(sortedSchedule) = ", len(sortedSchedule))
                if index >= len(sortedSchedule):
                    # print("wait for next day")
                    return                
                actionToday = now.replace(hour=sortedSchedule[index][0].hour, minute=sortedSchedule[index][0].minute, second=0)
                timeThreshold = now.replace(hour=sortedSchedule[index][0].hour, minute=sortedSchedule[index][0].minute, second=2)
                # print("action today = ", actionToday)
                # print("timeThreshold = ", timeThreshold)
                # print("now = ", now)
                if now >= actionToday:
                    if now < timeThreshold: 
                        if ("Close" in sortedSchedule[index][1] and "Close" in doorStatus) or ("Open" in sortedSchedule[index][1] and "Open" in doorStatus):
                            self.logger.debug("The door is already %s when the action %s was scheduled for %s", doorStatus, sortedSchedule[index][1], sortedSchedule[index][0])
                        else:
                            self.logger.debug("perform action - %s", sortedSchedule[index][1])
                            self.triggerDoor()
                        time.sleep(2)
                        return
                    # print("increment", actionToday, " ----- now = ", now)
                    index += 1
                elif now < actionToday:
                    # print("do nothing, waiting for - ", actionToday, " ----- now = ", now)
                    return
                else:
                    return
        except json.JSONDecodeError as e:
            self.logger.debug("JSON decode error: %s", e)
            return
        

    def scheduleThread(self):
        lastMod = datetime.min
        sortedSchedule = []
        while self.runProgram:
            modifiedTime = os.path.getmtime("doorData.json")
            readableTime = time.ctime(modifiedTime)

            if readableTime > lastMod:
                sortedSchedule = self.getScheduleActions()
            self.checkSchedule(sortedSchedule)


    def checkSchedule(self, sortedSchedule):
        now = datetime.datetime.now()
        index = 0
        while True:
            # print("len(sortedSchedule) = ", len(sortedSchedule))
            if index >= len(sortedSchedule):
                # print("wait for next day")
                return                
            actionToday = now.replace(hour=sortedSchedule[index][0].hour, minute=sortedSchedule[index][0].minute, second=0)
            timeThreshold = now.replace(hour=sortedSchedule[index][0].hour, minute=sortedSchedule[index][0].minute, second=2)
            # print("action today = ", actionToday)
            # print("timeThreshold = ", timeThreshold)
            # print("now = ", now)
            if now >= actionToday:
                if now < timeThreshold: 
                    if ("Close" in sortedSchedule[index][1] and "Close" in doorStatus) or ("Open" in sortedSchedule[index][1] and "Open" in doorStatus):
                        self.logger.debug("The door is already %s when the action %s was scheduled for %s", doorStatus, sortedSchedule[index][1], sortedSchedule[index][0])
                    else:
                        self.logger.debug("perform action - %s", sortedSchedule[index][1])
                        self.triggerDoor()
                    time.sleep(2)
                    return
                # print("increment", actionToday, " ----- now = ", now)
                index += 1
            elif now < actionToday:
                # print("do nothing, waiting for - ", actionToday, " ----- now = ", now)
                return
            else:
                return


    def getScheduleActions(self):
        scheduledActionsExist = False
        scheduledAction = []

        try:
            with open("doorData.json", "r+") as outfile:
                allData = json.load(outfile)
                # print("allData = ", allData)
                schedules = allData["scheduledActions"]
                doorStatus = allData["doorStatus"]
                # print("schedules = ", schedules)
                for schedule in schedules:
                    if schedule["runProgramToggleInput"]:
                        scheduledActionsExist = True
                        action = [datetime.datetime.strptime(schedule["timeInput"], "%H:%M"), schedule["openclosebuttonInput"]]
                        scheduledAction.append(action)
            sortedSchedule = sorted(scheduledAction)
            # print("sortedSchedule = ", sortedSchedule)
            return sortedSchedule
        except json.JSONDecodeError as e:
            self.logger.debug("JSON decode error: %s", e)
            return


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
        # imageCopy = carImage.copy()
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
                # print("License Contour Area = ", area)
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

    def lookForLicensePlateGpu(self, carImage):
        # carImage = cv2.resize(carImage, (640, 480))
        cv2.cuda.setDevice(config.gpu_id)
        carImageGpu = cv2.cuda.GpuMat()
        carImageGpu.upload(carImage)
        print("uploaded to gpu")

        if config.colorSpace == "RGB":
            grayCarImageGpu = cv2.cuda.cvtColor(carImageGpu, cv2.COLOR_BGR2GRAY)
            if grayCarImageGpu.empty():
                print("Error: grayCarImageGpu is empty")
            print("convereted to grey")
            cannyDetector = cv2.cuda.createCannyEdgeDetector(config.lowerCanny, config.upperCanny) 
            print("create edge detector")
            carEdgeImageGpu = cannyDetector.detect(grayCarImageGpu)
            print("run edge detector")
            carEdgeImage = carEdgeImageGpu.download()
            print("downloaded to cpu")
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
        print("Writing test images")
        cv2.imwrite("testImages/edgeImage.jpg", carEdgeImage)
        # boundingBoxArea = [None] * len(contours)
        minAreaDif = float('inf')
        minAreaDifIdx = -1
        count = 0
        # imageCopy = carImage.copy()
        self.logger.debug("About to search through contours: %s", len(contours))
        if len(contours) == 0:
            carImageGpu.release()
            grayCarImageGpu.release()
            carEdgeImageGpu.release()
            return (0,0,0,0)
        for contour in contours:
            imageCopy = carImage.copy()
            # boundRect = cv2.boundingRect(contour)
 
            area = cv2.contourArea(contour)
            # approxArea = cv2.contourArea(approx)
            # print("area = ", area)
            # print("approxArea = ", approxArea)
            if area > config.contourMinArea:
                ((x, y), (width, height), angle) = cv2.minAreaRect(contour)
                boundingBoxArea = width * height
                # print("License Contour Area = ", area)
                areaDif = abs(boundingBoxArea - area)
                # print("new contour = ", count)
                # print("boundingBoxArea = ", boundingBoxArea)
                # print("areaDif = ", areaDif)
                if areaDif < minAreaDif:
                    minAreaDif = areaDif
                    minAreaDifIdx = count
                    # print("---------------------------------------new min---------------------------------------")
                    self.logger.debug("Found a new closest bounding box to contour match - potentially a license plate at countor %s", count)
                    
                # upcomment this imshow lines and waitKey line for useful debug images
                # cv2.drawContours(imageCopy, contours, count, (0, 255, 0), 10)
                
                # cv2.drawContours(imageCopy, approx, -1, (0, 255, 0), 2)
                # cv2.drawContours(hsvCarImg, hsvContours, count, (0, 255, 0), 2)
                # cv2.imshow("hsv image", hsvGausBlur)
                # cv2.imshow("edge image", hsvCarEdgeImage)
                # cv2.imshow("diolated edge image", dilatedEdgeImage)
                # cv2.imshow("car image with contour", imageCopy)
                # cv2.waitKey(0)
                # cv2.destroyWindow("car image with contour")
                
            count += 1
        self.logger.debug("Completed look for license plate")
        if minAreaDifIdx != -1:
            finalBox = cv2.boundingRect(contours[minAreaDifIdx])
            cv2.rectangle(imageCopy, (finalBox[0], finalBox[1]), (finalBox[0]+finalBox[2], finalBox[1]+finalBox[3]), (255, 0, 0), 2)
        else:
            finalBox = cv2.boundingRect(contours[0])
            cv2.rectangle(imageCopy, (finalBox[0], finalBox[1]), (finalBox[0]+finalBox[2], finalBox[1]+finalBox[3]), (255, 0, 0), 2)
        # cv2.imwrite("testImages/contourImages/contourImages" + str(count) + ".jpg", imageCopy)

        carImageGpu.release()
        grayCarImageGpu.release()
        carEdgeImageGpu.release()
        del cannyDetector

        return finalBox

    def cameraThread(self, filename):
        #self.videoBuffer = deque()
        self.logger.debug("Starting camera thread")
        self.bufferReadyForFrame = True
        self.saveVideoComplete = False
        self.bufferActive = False
        # pipeline = (
        #     "rtspsrc location={} latency=100 protocols=tcp ! "
        #     "rtph265depay ! h265parse ! avdec_h265 ! videoconvert ! appsink"
        # ).format(filename)
        # self.capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        self.capture = cv2.VideoCapture(filename)
        self.ret, self.frame = self.capture.read()
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        if config.saveVideo:
            self.out = cv2.VideoWriter(config.saveVideoFileName, fourcc, 20.0, (1920, 1080))
        self.bufferOut = cv2.VideoWriter("bufferVideo.avi", fourcc, 20.0, (1920, 1080))
        while self.ret:
            self.ret, self.frame = self.capture.read()
            if config.saveVideo:
                self.out.write(self.frame)
            while not self.ret:
                print("Camera Disconected, trying to reconnect")
                self.logger.debug("Camera Disconected, trying to reconnect")
                time.sleep(1)
                self.readyForNewFrame = False
                self.capture.release()
                time.sleep(1)
                # self.capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                self.capture = cv2.VideoCapture(filename)
                self.ret, self.frame = self.capture.read()
            self.readyForNewFrame = True

            if 0xFF == ord('q'):
                self.capture.release()
                self.out.release()
                #self.bufferOut.release()
                self.runProgram = False
                self.runCheckDoor = False
                break
        print("video thread exit")
        self.logger.debug("Exiting Video Thread")

    def hearbeat(self):
        with open("heartbeat.txt", "w") as f:
            f.write(str(time.time()))        

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

    def runCameraMonitor(self, localAdjustCameraInstance):
        self.logger.debug("runCameraMonitor")
        localAdjustCameraInstance.checkModeVsTime()
        # cameraMode.adjustCamera().checkModeVsTime

garageDoorCam()
