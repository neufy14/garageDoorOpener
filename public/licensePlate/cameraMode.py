from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import datetime
from datetime import timezone
from suntime import Sun, SunTimeException
import geocoder
import json
import logging
from pyvirtualdisplay import Display


class adjustCamera:
    def __init__(self):
        logging.basicConfig(filename="cameraLog.log",
                format='%(asctime)s %(message)s',
                filemode='a')
        # Creating an object
        adjustCamera.settingsChange = False
        self.cameraLogger = logging.getLogger()
        self.cameraLogger.setLevel(logging.DEBUG)
        self.cameraLogger.debug("Starting camera mode program")
        jsonFilename = "cameraData.json"
        deviceLoc = geocoder.ip('me')
        adjustCamera.isDaytime = True

        while True:
            data = self.parseJson(jsonFilename)
            mode = data["currentMode"]
            dayNight = data["dayNight"]
            if mode == "auto":
                # self.cameraLogger.debug("Mode is auto")
                sunRise, sunSet = self.getSunHours(deviceLoc.latlng)
                currentTime = datetime.datetime.now(timezone.utc)
                timeCompare = currentTime > sunRise
                # self.cameraLogger.debug("Time compare test, currentTime > sunRise: %s", str(timeCompare))
                # print("dayNight = ", dayNight)
                if currentTime > sunRise and currentTime < sunSet:
                    adjustCamera.isDaytime = True
                    if dayNight == "night":
                        self.cameraLogger.debug("Switching to day mode automatically")
                        adjustCamera.settingsChange = True
                        # self.switchMode("day")
                        adjustCamera.settingsChange = False
                        data["dayNight"] = "day"
                        self.saveJson(jsonFilename, data)
                    # print("day time")
                else:
                    adjustCamera.isDaytime = False
                    if dayNight == "day":
                        adjustCamera.settingsChange = True
                        # self.switchMode("night")
                        adjustCamera.settingsChange = False
                        data["dayNight"] = "night"
                        self.saveJson(jsonFilename, data)
                        self.cameraLogger.debug("Switching to night mode automatically")
                    # print("night time")
                time.sleep(1)
            elif mode == "manual":
                if adjustCamera.isDaytime and dayNight == "night":
                    adjustCamera.isDaytime = False
                    adjustCamera.settingsChange = True
                    self.switchMode("night")
                    adjustCamera.settingsChange = False
                    self.cameraLogger.debug("Switching to night mode manually")
                elif not adjustCamera.isDaytime and dayNight == "day":
                    adjustCamera.isDaytime = True
                    adjustCamera.settingsChange = True
                    self.switchMode("day")
                    adjustCamera.settingsChange = False
                    self.cameraLogger.debug("Switching to day mode manually")


    def getSunHours(self, location):
        latitude = location[0]
        longitude = location[1]

        sun = Sun(latitude, longitude)

        # Get today's sunrise and sunset in UTC
        today_sr = sun.get_sunrise_time()
        today_ss = sun.get_sunset_time()

        return today_sr, today_ss

    def switchMode(self, mode):
        display = Display(visible=0, size=(800, 800))  
        display.start()
        self.cameraLogger.debug("Starting switch mode")
        # Path to your webdriver. For example, if you're using Chrome, you'd need chromedriver installed.
        # cService = webdriver.ChromeService(r"C:\Users\Alexn\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe")
        driver = webdriver.Chrome()

        # URL of the website you want to log in to
        url = 'http://192.168.0.100/'

        self.cameraLogger.debug("Getting URL")
        # Open the URL in the browser
        driver.get(url)

        # Find the username and password input fields (you need to inspect the HTML of the webpage to identify these elements)
        username_input = driver.find_element(By.ID, "username")  # Example ID, replace with actual ID of username input field
        time.sleep(0.1)
        username_input.send_keys('admin')

        time.sleep(0.1)

        # Enter your username and password
        password_input = driver.find_element(By.ID, 'password')  # Example ID, replace with actual ID of password input field
        password_input.send_keys('Steelers12')

        time.sleep(0.1)
        self.cameraLogger.debug("Enter login information")
        # Find and click the login button
        login_button = driver.find_element(By.ID, 'b_login')  # Example ID, replace with actual ID of login button
        time.sleep(0.1)
        login_button.click()

        time.sleep(0.5)
        self.cameraLogger.debug("Press login button")
        # Find and click the Configuration tab
        configuration_tab = driver.find_element(By.ID, 'b_c')
        time.sleep(0.1)
        configuration_tab.click()
        time.sleep(2)
        self.cameraLogger.debug("Camera page loaded")
        if mode == "night":
            print("switching to night")
            id = "IRCutManual_NightMode"
            irButton = driver.find_element(By.ID, id)
        if mode == "day":
            print("switching to day")
            id = "IRCutManual_DayMode"
            irButton = driver.find_element(By.ID, id)
        time.sleep(0.1)
        irButton.click()
        self.cameraLogger.debug("Saving changes")
        saveButton = driver.find_element(By.ID, "camera_confirm")
        time.sleep(3)
        saveButton.click()
        time.sleep(0.1)
        self.cameraLogger.debug("Done")
        # Close the browser window
        driver.quit()


    def parseJson(self, filename):
        jsonFile = open(filename)
        jsonData = json.load(jsonFile)
        jsonFile.close()
        return jsonData

    def saveJson(self, filename, data):
        with open(filename, "w") as outfile:
            json.dump(data, outfile)

# adjustCamera()