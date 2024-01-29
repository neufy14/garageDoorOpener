import time
import threading
import cv2
import numpy as np
from easyocr import Reader
import config

class garageDoorCam:
    def __init__(self):
        print("start")
        # self.videoFile = 0
        self.readyForNewFrame = False
        # color = (255, 0, 0)
        thickness = 2
        # Model
        # model = torch.hub.load('yolov5', "yolov5n", source="local")  # or yolov5n - yolov5x6, custom
        model = YoloTRT(library=cofig.libLoc, engine=config.engineLoc, conf=config.modelConf, yolo_ver="v5")
        print("model.names = ", model.names)
        print("model.names[3] = ", model.names[3])
        np.random.seed(42)
        COLORS = np.random.randint(0, 255, size=(len(model.names), 3),
                                   dtype="uint8")

        print("[INFO] loading EAST text detector...")
        # net = cv2.dnn.readNet(config.textDetectionModel)

        language = 'en'.split(",")
        reader = Reader(language)
        print("loading easyOCR")
        if config.useLiveVideo:
            # start camera thread to get live video feed
            videoThread = threading.Thread(target=self.cameraThread, args=(config.videoFile,))
            videoThread.start()
        else:
            self.capture = cv2.VideoCapture(config.savedVideoFile)
            self.ret, self.frame = self.capture.read()
            self.readyForNewFrame = True
        frameNumber = 0
        successIdentification = 0
        # input("Press Enter to continue...")
        while True:
            if self.readyForNewFrame:
                frameNumber += 1
                self.readyForNewFrame = False
                if not config.useLiveVideo:
                    self.ret, self.frame = self.capture.read()
                    if self.ret == False:
                        break
                    self.readyForNewFrame = True
                # Inference
                start = time.time()
                results = model(self.frame)
                # end = time.time()
                # print("[INFO] YOLO took {:.6f} seconds".format(end - start))
                # Results
                results.print()
                foundText = []
                upperleft = []
                buttomRight = []
                count = 0
                for output in results.xyxy[0]:
                    upperleft = (int(output[0]), int(output[1]))
                    buttomRight = (int(output[2]), int(output[3]))
                    # color = [int(c) for c in COLORS[classIDs[output[5]]]]
                    if model.names[int(output[5])] in config.validSkus and output[5] > config.modelConfidence:
                        modelName = "{}: {:.4f}".format(model.names[int(output[5])], output[4])
                        color = (int(COLORS[int(output[5])][0]), int(COLORS[int(output[5])][1]),
                                 int(COLORS[int(output[5])][2]))

                        # cropped image based off full car bounding box
                        # croppedImage = self.frame[int(output[1]):int(output[3]), int(output[0]):int(output[2]), :]
                        # croppedImage = self.frame[int(output[1]):int(output[3]), int(yStart):int(output[2]), :]

                        # cropped image based off car bottom half bounding box
                        yStart = (output[1] + output[3]) / 4
                        # cv2.imshow("blank image", self.frame)
                        croppedImage = self.frame[int(yStart):int(output[3]), int(output[0]):int(output[2]), :]
                        # croppedImage = cv2.resize(croppedImage, (0, 0), fx = 0.9, fy = 0.9)

                        # startOcr = time.time()
                        # cropped image based off looking for license plate inside car bounding box
                        (tlx, tly, cropWidth, cropHeight) = self.lookForLicensePlate(croppedImage)
                        corners = [(tly-config.erodeAmount), (tly+cropWidth+config.erodeAmount), (tlx-config.erodeAmount), (tlx+cropWidth+config.erodeAmount)]

                        # print("len(croppedImage) = ", len(croppedImage))
                        # print("len(croppedImage[0]) = ", len(croppedImage[0]))
                        for i in range(len(corners)):
                            if corners[i] < 0:
                                corners[i] = 0
                            if i < 2 and corners[i] > abs(int(yStart) - int(output[3])):
                                corners[i] = len(croppedImage)
                            elif i > 1 and corners[i] > abs(int(output[0] - int(output[2]))):
                                corners[i] = len(croppedImage[0])

                        # licenseImage = croppedImage[(tly-config.erodeAmount):(tly+cropWidth+config.erodeAmount),
                        #                (tlx-config.erodeAmount):(tlx+cropWidth+config.erodeAmount)]
                        licenseImage = croppedImage[corners[0]:corners[1], corners[2]:corners[3]]


                        # print("original image shape = ", self.frame.shape)
                        # print("cropped image shape = ", croppedImage.shape)

                        # grayCroppedImage = cv2.cvtColor(croppedImage, cv2.COLOR_BGR2GRAY)

                        # cv2.imshow("cropped image", croppedImage)
                        # cv2.imshow("license image", licenseImage)
                        # cv2.waitKey(0)

                        imageText = self.lookForText(licenseImage, reader)
                        self.frame = cv2.rectangle(self.frame, upperleft, buttomRight, color, thickness)
                        cv2.putText(self.frame, modelName, (upperleft[0], upperleft[1] - 5), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5, color, 2)
                        # cv2.rectangle(croppedImage, (tlx, tly), (tlx + cropWidth, tly + cropHeight), (0, 255, 0), 2)

                        # endOcr = time.time()
                        # print("[INFO] OCR took {:.6f} seconds".format(endOcr - startOcr))
                        for (bbox, text, probability) in imageText:
                            plateFound = False
                            for char in config.chars2Ignore:
                                text = text.replace(char, "")
                            for validPlate in config.validPlates:
                                if validPlate in text:
                                    textColor = (50, 255, 0)
                                    plateFound = True
                                    successIdentification += 1
                                elif validPlate not in text and not plateFound:
                                    textColor = (0, 0, 255)
                            # if text in config.validPlates:
                            #     textColor = (50, 255, 0)
                            #     successIdentification += 1
                            # else:
                            #     textColor = (0, 0, 255)
                            (tl, tr, br, bl) = bbox
                            # tl = (int(tl[0] + output[0] + tlx), int(tl[1] + output[1] + tly))
                            tl = (int(tl[0] + output[0]), int(tl[1] + output[1]))
                            tr = (int(tr[0] + output[0]), int(tr[1] + output[1]))
                            bl = (int(bl[0] + output[0]), int(bl[1] + output[1]))
                            br = (int(br[0] + output[0]), int(br[1] + output[1]))
                            cv2.rectangle(self.frame, upperleft, buttomRight, color, thickness)
                            cv2.rectangle(self.frame, (corners[0], corners[1]), (corners[2], corners[3]), (0,255,255), thickness)
                            cv2.putText(self.frame, text, (tl[0], tl[1] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                        2, textColor, 2)
                            print("text = ", text)
                    count += 1
                cv2.putText(self.frame, str(frameNumber), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 4)
                # for i in range(count):
                #     self.frame = cv2.rectangle(self.frame, upperleft[i], buttomRight[i], color, thickness)
                cv2.imshow('frame', self.frame)
                end = time.time()
                print("[INFO] Processing took {:.6f} seconds".format(end - start))
                print("[INFO] Frame rate is: ", (1 / (end - start)), "FPS")
                if cv2.waitKey(1) & 0xFF == ord('q') or self.ret == False:
                    self.capture.release()
                    # self.out.release()
                    break
        print("main thread exit")
        print("Successful Identification Percentage = ", (successIdentification / frameNumber))
        videoThread.join()

        cv2.destroyAllWindows()


        # # test single image
        # img = "70.jpg"
        # results = model(img)
        # results.print()
        # results.show()  # or .show(), .save(), .crop(), .pandas(), etc.
        # for coords in results.xyxy:
        #     print("coords = ", coords)

    def lookForText(self, image, read):
        # cv2.imshow("cropped image", image)
        results = read.readtext(image)
        print("results = ", results)
        return results

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
        self.capture = cv2.VideoCapture(filename)
        self.ret, self.frame = self.capture.read()
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter(config.saveVideoFileName, fourcc, 20.0, (1920, 1080))
        while self.ret:
            # self.capture = cv2.VideoCapture(self.videoFile)
            self.ret, self.frame = self.capture.read()
            if config.saveVideo:
                self.out.write(self.frame)
            self.readyForNewFrame = True
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.capture.release()
                self.out.release()
                break
        print("video thread exit")

    # def warpLicensePlate(self, plateImage):
    #     #use getPerspectiveTransform and warpPerspective to square up the license plate image before passing to OCR

garageDoorCam()
