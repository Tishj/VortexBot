from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from datetime import datetime

import json, time, random
import PIL.ImageOps 
try:
	from PIL import Image,ImageEnhance, ImageFilter
except ImportError:
	import Image
import pytesseract
from io import BytesIO
import sys

#--------------------------------------INCLUDES--------------------------------------

current_time = time.time()
names = sys.argv[1::]
log = open("log", "a+")


def get_string_from_image(image):
	width, height = image.size
	image = image.resize((width * 4, height * 4), PIL.Image.BICUBIC)
	image = image.filter(ImageFilter.SHARPEN)
	image = image.filter(ImageFilter.SMOOTH)
	image = ImageEnhance.Contrast(image).enhance(1.5)
	image = image.point(lambda i: i > 185 and 255)
	image = PIL.ImageOps.invert(image)
	config = "--psm 6 -c tessedit_char_whitelist=0123456789KMT" #magby
	text = pytesseract.image_to_string(image, config=config)
	print("pokemon found:",text)
	return text

def dispatchKeyEvent(driver, name, options = {}):
	options["type"] = name
	body = json.dumps({'cmd': 'Input.dispatchKeyEvent', 'params': options})
	resource = "/session/%s/chromium/send_command" % driver.session_id
	url = driver.command_executor._url + resource
	driver.command_executor._request('POST', url, body)

def analyze_screenshot(driver):
	screenshot = driver.get_screenshot_as_png()
	image = Image.open(BytesIO(screenshot))
	image = PIL.ImageOps.grayscale(image)
	image = image.crop((301,305,646,325))
#	image.save("/c/users/thijs/desktop/codam/vortexbot/pokemon" + datetime.datetime.now().strftime("%m_%d_%H_%M_%S") + ".png")
	Pokimane = get_string_from_image(image).replace(" ", "")
	global names
	for name in names:
		if name in Pokimane.lower(): quit()
	log.write(Pokimane)
	return False

# def CheckPokemon(driver):
# 	while True:
# 		mutex.acquire(1)
# 		isInteresting(driver)
# 		mutex.release()
# 		time.sleep(1)

def holdKey(driver, duration, key):
	global current_time
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
		options["autoRepeat"] = True
		if time.time() >= current_time + 2:
			current_time = time.time()
			analyze_screenshot(driver)
		else:
			time.sleep(0.01)

from threading import Thread
from time import sleep

#---------------------------------------SETUP--------------------------------------------



print(names)

PATH = "./req/chromedriver.exe"
WINDOW_SIZE = "1920,1080"

WINDOW_SIZE = "1920,1080"

driver = webdriver.Chrome(PATH)

driver.get("https://www.pokemon-vortex.com/login/")
username_field = driver.find_element_by_id("myusername")
password_field = driver.find_element_by_id("mypassword")
login_button = driver.find_element_by_id("submit")

username_field.send_keys("Shadow4Kingz")
password_field.send_keys("testtest")
login_button.send_keys(Keys.RETURN)

driver.get("https://www.pokemon-vortex.com/map-select/")

time.sleep(5)

pokeName = driver.execute_script("function getPokemonName() { return(Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeName._text) }; getPokemonName()")
#pokeName = driver.execute_script("getPokemonName()")

print(pokeName)

quit()

#------------------------------------LOOP-----------------------------------

offset = 0

current_time = time.time()


while (True):
	left_interval = random.randrange(10,35)
	holdKey(driver, (offset + left_interval) / 100, "D")
	offset = left_interval
	right_interval = random.randrange(10,35)
	holdKey(driver, (offset + right_interval) / 100, "A")
	offset = right_interval
	# time.sleep(0.5)