from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from datetime import datetime

import json, time, random
import PIL.ImageOps 
try:
	from PIL import Image,ImageEnhance, ImageFilter
except ImportError:
	import Image
import pytesseract
from io import BytesIO

#--------------------------------------INCLUDES--------------------------------------

current_time = time.time()
log = open("log", "a+")

def get_string_from_image(image):
	width, height = image.size
	image = image.resize((width * 4, height * 4), PIL.Image.BICUBIC)
	try:
		image = PIL.ImageOps.grayscale(image)
		image = PIL.ImageOps.invert(image)
	except:
		pass
	image = ImageEnhance.Contrast(image).enhance(1.5)
	image = image.point(lambda i: not i > 75 and 255)
	image = PIL.ImageOps.invert(image)
	config = "--psm 6 -c tessedit_char_whitelist=0123456789KMT" #magby
	text = pytesseract.image_to_string(image, config=config)
	return text

def dispatchKeyEvent(driver, name, options = {}):
	options["type"] = name
	body = json.dumps({'cmd': 'Input.dispatchKeyEvent', 'params': options})
	resource = "/session/%s/chromium/send_command" % driver.session_id
	url = driver.command_executor._url + resource
	driver.command_executor._request('POST', url, body)

def isInteresting(driver):
	screenshot = driver.get_screenshot_as_png()
	image = Image.open(BytesIO(screenshot))
	image = image.crop((301,305,665,323))
	image.save("/c/users/thijs/desktop/codam/vortexbot/screenshot.png")
	Pokimane = get_string_from_image(image)
	log.write(Pokimane)
	current_time = time.time()
	return False

def holdKey(driver, duration, key):
	endtime = time.time() + duration
	options = { \
	"code": "Key",
	"key": "",
	"text": "",
	"unmodifiedText": "",
	"nativeVirtualKeyCode": 0,
	"windowsVirtualKeyCode": 0
	}
	options["code"] += key
	options["key"] += key.lower()
	options["text"] += key.lower()
	options["unmodifiedText"] += key.lower()
	options["nativeVirtualKeyCode"] = ord(key)
	options["windowsVirtualKeyCode"] = ord(key)
	while True:
		dispatchKeyEvent(driver, "rawKeyDown", options)
		dispatchKeyEvent(driver, "char", options)

		if time.time() > endtime:
			dispatchKeyEvent(driver, "keyUp", options)
			break
		if time.time() > current_time + 2:
			if isInteresting(driver) == True:
				quit()
		options["autoRepeat"] = True
		time.sleep(0.01)

from threading import Thread
from time import sleep

def threaded_function(arg):
	for i in range(arg):
		print("running")
		sleep(1)

#---------------------------------------MAIN--------------------------------------------

PATH = "./req/chromedriver.exe"

driver = webdriver.Chrome(PATH)

driver.get("https://www.pokemon-vortex.com/login/")
username_field = driver.find_element_by_id("myusername")
password_field = driver.find_element_by_id("mypassword")
login_button = driver.find_element_by_id("submit")

username_field.send_keys("Shadow4Kingz")
password_field.send_keys("testtest")
login_button.send_keys(Keys.RETURN)

driver.get("https://www.pokemon-vortex.com/map-select/")

steps = 0

while (True):
	left_interval = random.randrange(50, 125)
	right_interval = random.randrange(50, 125)
	holdKey(driver, left_interval / 100, "D")
	holdKey(driver, right_interval / 100, "A")
	steps += 1
	if steps > 20:
		break