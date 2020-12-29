from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from selenium.webdriver.common.by import By
from datetime import datetime

from threading import Thread, Lock
import json, time, random, sys, os
import pokebase as pb
import re

#--------------------------------------INCLUDES--------------------------------------

class Player:
	def __init__(self, driver):
		self.pokemons = []
		self.items = []
		self.driver = driver

	def move(self, location):
		world = {	'map' : "https://www.pokemon-vortex.com/map-select/",
					'team' : "https://www.pokemon-vortex.com/team/",
					'sidequest' : "https://www.pokemon-vortex.com/battle-sidequest/"}
		if self.driver.current_url == world[location]:
			return
		self.driver.get(world[location])

	def login(self):
		config = open("config", "r")
		username, password = config.read().split('\n')
		self.driver.get("https://www.pokemon-vortex.com/login/")
		username_field = self.driver.find_element_by_id("myusername")
		password_field = self.driver.find_element_by_id("mypassword")
		login_button = self.driver.find_element_by_id("submit")

		username_field.send_keys(username)
		password_field.send_keys(password)
		login_button.send_keys(Keys.RETURN)

	def init_team(self):
		self.move('team')
		raw_data = self.driver.find_element(by=By.CLASS_NAME, value="cards-group").text.split('\n')
		info = [raw_data[x:x+9] for x in range(0, len(raw_data), 9)]
		for i in range(info):
			self.pokemons.append(Pokemon(info[i][0], info[i][1], "", info[i][5:9]))

	def sidequest(self):
		self.move('sidequest')

		#init enemy

		raw_data = self.driver.find_element(by=By.ID, value="opponentPoke").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		enemies = []
		for i in range(info):
			enemies.append(Pokemon(info[i][0], info[i][1], info[i][2]))

		#init ally

		raw_data = self.driver.find_element(by=By.ID, value="pokeChoose").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i, pokemon in enumerate(self.pokemons):
			pokemon.hp = int(info[i][2].split(' ')[-1])

		#while there are still enemies left

		#pick a pokemon against enemy
		#fight until either dies:
			#if enemy:
				#move on
			#else:
				#pick second best option


class Item:
	def __init__(self):
		self.name = ""
		self.quantity = 0

class Pokemon:
	def __init__(self, name="", level="", hp="", moves=[]):
		self.special = ""
		self.moves = []
		self.types = []
		if not name:
			self.name = ""
		else:
			fullname = re.sub(r'[\(\.\'\)]', '', name.lower()).split(' ')
			if fullname[0] in ["metallic","shiny","shadow","mystic","dark"]:
				self.special = fullname[0]
				self.name = "-".join(fullname[1:]) 
			else:
				self.name = "-".join(fullname)
			self.types = [str(poketype.type) for poketype in pb.pokemon(self.name).types]
		if not level:
			self.level = 0
		else:
			self.level = int(level.split(' ')[-1])
		if not hp:
			self.hp = -1
		else:
			self.hp = int(hp.split(' ')[-1])
		if moves:
			for move in moves:
				self.moves.append(Move(move.replace(' ', '-').lower()))

class Move:
	def __init__(self, name = ""):
		self.name = name
		if name != "":
			self.type = pb.move(self.name).type
			self.power = pb.move(self.name).power
		self.type = ""
		self.power = 0

def get_type_multiplier(dmgtype, weaknesses):
	multipliers = {	'normal': {'normal': 1, 'fight': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 0.5, 'bug': 1, 'ghost': 0, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 1},
					'fight': {'normal': 2, 'fight': 1, 'flying': 0.5, 'poison': 0.5, 'ground': 1, 'rock': 2, 'bug': 0.5, 'ghost': 0, 'steel': 2, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 0.5, 'ice': 2, 'dragon': 1, 'dark': 2, 'fairy': 0.5},
					'flying': {'normal': 1, 'fight': 2, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 0.5, 'bug': 2, 'ghost': 1, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 2, 'electric': 0.5, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 1},
					'poison': {'normal': 1, 'fight': 1, 'flying': 1, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'bug': 1, 'ghost': 0.5, 'steel': 0, 'fire': 1, 'water': 1, 'grass': 2, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 2},
					'ground': {'normal': 1, 'fight': 1, 'flying': 0, 'poison': 2, 'ground': 1, 'rock': 2, 'bug': 0.5, 'ghost': 1, 'steel': 2, 'fire': 2, 'water': 1, 'grass': 0.5, 'electric': 2, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 1},
					'rock': {'normal': 1, 'fight': 0.5, 'flying': 2, 'poison': 1, 'ground': 0.5, 'rock': 1, 'bug': 2, 'ghost': 1, 'steel': 0.5, 'fire': 2, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 2, 'dragon': 1, 'dark': 1, 'fairy': 1},
					'bug': {'normal': 1, 'fight': 0.5, 'flying': 0.5, 'poison': 0.5, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 0.5, 'steel': 0.5, 'fire': 0.5, 'water': 1, 'grass': 2, 'electric': 1, 'psychic': 2, 'ice': 1, 'dragon': 1, 'dark': 2, 'fairy': 0.5},
					'ghost': {'normal': 0, 'fight': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 2, 'steel': 1, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 2, 'ice': 1, 'dragon': 1, 'dark': 0.5, 'fairy': 1},
					'steel': {'normal': 1, 'fight': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 2, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 0.5, 'grass': 1, 'electric': 0.5, 'psychic': 1, 'ice': 2, 'dragon': 1, 'dark': 1, 'fairy': 2},
					'fire': {'normal': 1, 'fight': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 0.5, 'bug': 2, 'ghost': 1, 'steel': 2, 'fire': 0.5, 'water': 0.5, 'grass': 2, 'electric': 1, 'psychic': 1, 'ice': 2, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
					'water': {'normal': 1, 'fight': 1, 'flying': 1, 'poison': 1, 'ground': 2, 'rock': 2, 'bug': 1, 'ghost': 1, 'steel': 1, 'fire': 2, 'water': 0.5, 'grass': 0.5, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
					'grass': {'normal': 1, 'fight': 1, 'flying': 0.5, 'poison': 0.5, 'ground': 2, 'rock': 2, 'bug': 0.5, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 2, 'grass': 0.5, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
					'electric': {'normal': 1, 'fight': 1, 'flying': 2, 'poison': 1, 'ground': 0, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 1, 'fire': 1, 'water': 2, 'grass': 0.5, 'electric': 0.5, 'psychic': 1, 'ice': 1, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
					'psychic': {'normal': 1, 'fight': 2, 'flying': 1, 'poison': 2, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 0.5, 'ice': 1, 'dragon': 1, 'dark': 0, 'fairy': 1},
					'ice': {'normal': 1, 'fight': 1, 'flying': 2, 'poison': 1, 'ground': 2, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 0.5, 'grass': 2, 'electric': 1, 'psychic': 1, 'ice': 0.5, 'dragon': 2, 'dark': 1, 'fairy': 1},
					'dragon': {'normal': 1, 'fight': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 2, 'dark': 1, 'fairy': 0},
					'dark': {'normal': 1, 'fight': 0.5, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 2, 'steel': 1, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 2, 'ice': 1, 'dragon': 1, 'dark': 0.5, 'fairy': 0.5},
					'fairy': {'normal': 1, 'fight': 2, 'flying': 1, 'poison': 0.5, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 2, 'dark': 2, 'fairy': 1}}
	mult = 1
	for weakness in weaknesses:
		if multipliers[dmgtype][weakness] == 0:
			return 0
		mult *= multipliers[dmgtype][weakness]
	return mult
#------------------------------------------------------------------------------------

names = sys.argv[1::]
#log = open("log_" + datetime.now().strftime("%d-%m-%Y_%H-%M"), "w+")

def dispatchKeyEvent(driver, name, options = {}):
	options["type"] = name
	body = json.dumps({'cmd': 'Input.dispatchKeyEvent', 'params': options})
	resource = "/session/%s/chromium/send_command" % driver.session_id
	url = driver.command_executor._url + resource
	driver.command_executor._request('POST', url, body)

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
		options["autoRepeat"] = True
		time.sleep(0.01)

def check_pokemon_name(mutex):
	last_pokemon = ""
	global log
	while True:
		mutex.acquire(1)
		driver.execute_script('document.querySelector("#logout").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeName._text')
		pokeName = driver.find_element_by_id("logout").get_attribute("text")
		mutex.release()
		pokeName = pokeName.lower().replace(' ', '')
		if pokeName != last_pokemon:
			log.write(pokeName + "\n")
			print("pokemon name:", pokeName)
			for name in names:
				if name in pokeName:
					log.close()
					os._exit(0)
		last_pokemon = pokeName
		time.sleep(1)

PATH = "./req/chromedriver.exe"
driver = webdriver.Chrome(PATH)
player = Player(driver)

player.login()
player.move('team')
#player.init_team()
player.sidequest()
quit()
#------------------------------------LOOP-----------------------------------

mutex = Lock()
thread = Thread(target=check_pokemon_name, args=(mutex,))

time.sleep(1)
thread.start()

#find_pokemon
offset = 0
while (True):
	left_interval = random.randrange(10,35)
	holdKey(player.driver, (offset + left_interval) / 100, "D")
	offset = left_interval
	right_interval = random.randrange(10,35)
	holdKey(player.driver, (offset + right_interval) / 100, "A")
	offset = right_interval