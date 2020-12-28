from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from datetime import datetime

from threading import Thread, Lock
import json, time, random, sys, os

#--------------------------------------INCLUDES--------------------------------------

current_time = time.time()
names = sys.argv[1::]
log = open("log", "a+")

def dispatchKeyEvent(driver, name, options = {}):
	options["type"] = name
	body = json.dumps({'cmd': 'Input.dispatchKeyEvent', 'params': options})
	resource = "/session/%s/chromium/send_command" % driver.session_id
	url = driver.command_executor._url + resource
	driver.command_executor._request('POST', url, body)

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
		time.sleep(0.01)

def check_pokemon_name(mutex):
	while True:
		mutex.acquire(1)
		driver.execute_script('document.querySelector("#logout").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeName._text')
		pokeName = driver.find_element_by_id("logout").get_attribute("text")
		mutex.release()
		pokeName = pokeName.lower().replace(' ', '')
		print("pokemon name:", pokeName)
		for name in names:
			if name in pokeName:
				print("FOUND IT")
				os._exit(0)
		time.sleep(1)

#---------------------------------------SETUP--------------------------------------------

# load the desired webpage

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

#------------------------------------LOOP-----------------------------------

current_time = time.time()
mutex = Lock()
thread = Thread(target=check_pokemon_name, args=(mutex,))

time.sleep(1)
thread.start()

offset = 0
while (True):
	left_interval = random.randrange(10,35)
	holdKey(driver, (offset + left_interval) / 100, "D")
	offset = left_interval
	right_interval = random.randrange(10,35)
	holdKey(driver, (offset + right_interval) / 100, "A")
	offset = right_interval