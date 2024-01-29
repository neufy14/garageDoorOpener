videoFile = "rtsp://admin:Steelers12@192.168.0.100/media/video1"
# videoFile = 0
savedVideoFile = "testVideo/laurensCar.mp4"
textImageTargetHeight = 320
textImageTargetWidth = 320
saveVideo = False
useLiveVideo = True
saveVideoFileName = "testVideo/video3.avi"
layerNames = [
	"feature_fusion/Conv_7/Sigmoid",
	"feature_fusion/concat_3"]
textDetectionModel = "frozen_east_text_detection.pb"
downSizeRatio = 0.5
validPlates = ['9AH824', "BL27576", "2RGB55", "212YDL"]
lowerCanny = 100
upperCanny = 200
contourMinArea = 1000
modelConfidence = 0.01
validSkus = ['car', 'truck', 'suitcase']
# validSkus = ['none']
erodeAmount = 25
chars2Ignore = [" ", ",", ".", "*", "+", "[", "]", "(", ")", ";", ":", "'", '"']
aperture_size = 5
colorSpace = "RGB"
libLoc = "JetsonYolov5/yolov5/build/libmyplugins.so"
engineLoc = "JetsonYolov5/yolov5/build/yolov5s.engine"
confidenceThresh = 0.01
setDoorPin = 16
readDoorPin = 18
videoBufferLength = 100
maxStoredImages = 100
deleteAfterTime = 30