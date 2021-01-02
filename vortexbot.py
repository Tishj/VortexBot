from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from selenium.webdriver.common.by import By
from datetime import datetime

from threading import Thread, Lock
import json, time, random, sys, os
import re
import pickle
import copy

#damage = (lvl * power * STAB) * modifier / 60

#--------------------------------------INCLUDES--------------------------------------

#load the database, if missing or outdated, run `update_movedb.py`
with open('movedb', 'rb') as f:
	move_library = pickle.load(f)
with open('pokedb', 'rb') as f:
	pokedb = pickle.load(f)
multipliers = {	'normal': {'normal': 1, 'fighting': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 0.5, 'bug': 1, 'ghost': 0, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 1},
				'fighting': {'normal': 2, 'fighting': 1, 'flying': 0.5, 'poison': 0.5, 'ground': 1, 'rock': 2, 'bug': 0.5, 'ghost': 0, 'steel': 2, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 0.5, 'ice': 2, 'dragon': 1, 'dark': 2, 'fairy': 0.5},
				'flying': {'normal': 1, 'fighting': 2, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 0.5, 'bug': 2, 'ghost': 1, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 2, 'electric': 0.5, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 1},
				'poison': {'normal': 1, 'fighting': 1, 'flying': 1, 'poison': 0.5, 'ground': 0.5, 'rock': 0.5, 'bug': 1, 'ghost': 0.5, 'steel': 0, 'fire': 1, 'water': 1, 'grass': 2, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 2},
				'ground': {'normal': 1, 'fighting': 1, 'flying': 0, 'poison': 2, 'ground': 1, 'rock': 2, 'bug': 0.5, 'ghost': 1, 'steel': 2, 'fire': 2, 'water': 1, 'grass': 0.5, 'electric': 2, 'psychic': 1, 'ice': 1, 'dragon': 1, 'dark': 1, 'fairy': 1},
				'rock': {'normal': 1, 'fighting': 0.5, 'flying': 2, 'poison': 1, 'ground': 0.5, 'rock': 1, 'bug': 2, 'ghost': 1, 'steel': 0.5, 'fire': 2, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 2, 'dragon': 1, 'dark': 1, 'fairy': 1},
				'bug': {'normal': 1, 'fighting': 0.5, 'flying': 0.5, 'poison': 0.5, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 0.5, 'steel': 0.5, 'fire': 0.5, 'water': 1, 'grass': 2, 'electric': 1, 'psychic': 2, 'ice': 1, 'dragon': 1, 'dark': 2, 'fairy': 0.5},
				'ghost': {'normal': 0, 'fighting': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 2, 'steel': 1, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 2, 'ice': 1, 'dragon': 1, 'dark': 0.5, 'fairy': 1},
				'steel': {'normal': 1, 'fighting': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 2, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 0.5, 'grass': 1, 'electric': 0.5, 'psychic': 1, 'ice': 2, 'dragon': 1, 'dark': 1, 'fairy': 2},
				'fire': {'normal': 1, 'fighting': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 0.5, 'bug': 2, 'ghost': 1, 'steel': 2, 'fire': 0.5, 'water': 0.5, 'grass': 2, 'electric': 1, 'psychic': 1, 'ice': 2, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
				'water': {'normal': 1, 'fighting': 1, 'flying': 1, 'poison': 1, 'ground': 2, 'rock': 2, 'bug': 1, 'ghost': 1, 'steel': 1, 'fire': 2, 'water': 0.5, 'grass': 0.5, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
				'grass': {'normal': 1, 'fighting': 1, 'flying': 0.5, 'poison': 0.5, 'ground': 2, 'rock': 2, 'bug': 0.5, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 2, 'grass': 0.5, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
				'electric': {'normal': 1, 'fighting': 1, 'flying': 2, 'poison': 1, 'ground': 0, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 1, 'fire': 1, 'water': 2, 'grass': 0.5, 'electric': 0.5, 'psychic': 1, 'ice': 1, 'dragon': 0.5, 'dark': 1, 'fairy': 1},
				'psychic': {'normal': 1, 'fighting': 2, 'flying': 1, 'poison': 2, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 0.5, 'ice': 1, 'dragon': 1, 'dark': 0, 'fairy': 1},
				'ice': {'normal': 1, 'fighting': 1, 'flying': 2, 'poison': 1, 'ground': 2, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 0.5, 'grass': 2, 'electric': 1, 'psychic': 1, 'ice': 0.5, 'dragon': 2, 'dark': 1, 'fairy': 1},
				'dragon': {'normal': 1, 'fighting': 1, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 2, 'dark': 1, 'fairy': 0},
				'dark': {'normal': 1, 'fighting': 0.5, 'flying': 1, 'poison': 1, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 2, 'steel': 1, 'fire': 1, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 2, 'ice': 1, 'dragon': 1, 'dark': 0.5, 'fairy': 0.5},
				'fairy': {'normal': 1, 'fighting': 2, 'flying': 1, 'poison': 0.5, 'ground': 1, 'rock': 1, 'bug': 1, 'ghost': 1, 'steel': 0.5, 'fire': 0.5, 'water': 1, 'grass': 1, 'electric': 1, 'psychic': 1, 'ice': 1, 'dragon': 2, 'dark': 2, 'fairy': 1}}
names = sys.argv[1::]
found = False

PATH = "./req/chromedriver.exe"
driver = webdriver.Chrome(PATH)

#-------------------------------FUNCTIONS---------------------------------------------

def dispatchKeyEvent(driver, name, options = {}):
	options["type"] = name
	body = json.dumps({'cmd': 'Input.dispatchKeyEvent', 'params': options})
	resource = "/session/%s/chromium/send_command" % driver.session_id
	url = driver.command_executor._url + resource
	driver.command_executor._request('POST', url, body)

def holdKey(driver, pokefound, duration, key):
	global found
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

		pokefound.acquire(1)
		if time.time() > endtime or found == True:
			dispatchKeyEvent(driver, "keyUp", options)
			pokefound.release()
			break
		pokefound.release()
		options["autoRepeat"] = True
		time.sleep(0.01)

def check_pokemon_name(mutex, pokefound):
	last_pokemon = ""
	global found
#	global log
	time.sleep(1)
	while True:
		mutex.acquire(1)
		driver.execute_script('document.querySelector("#logout").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeName._text')
		pokeName = driver.find_element_by_id("logout").get_attribute("text")
		mutex.release()
		pokeName = pokeName.lower().replace(' ', '')
		if pokeName != last_pokemon:
#			log.write(pokeName + "\n")
			print("pokemon name:", pokeName)
			for name in names:
				if name in pokeName:
					print("FOUND POKEMON")
					pokefound.acquire(1)
					found = True
					pokefound.release()
					return
		last_pokemon = pokeName
		time.sleep(1)

def target_catchable_reached(enemy_hp):
	return True if (enemy_hp >= 1 and enemy_hp <= 30) else False

def target_sidequest_reached(enemy_hp):
	return True if enemy_hp <= 0 else False

def get_type_multiplier(dmgtype, weaknesses):
	mult = 1
	for weakness in weaknesses:
		if multipliers[dmgtype][weakness] == 0:
			return 0
		mult *= multipliers[dmgtype][weakness]
	return mult

def simulate_scenarios(destination, hp, moves, funct, history=[]):
#	print(hp)
	if funct(hp): #if target hp is reached
#		print(history)
		return destination.append(history)
	if hp <= 0 or (history and len(history) >= 8): #if it died when we didnt want it to die or this path is garbage
		return
	for move in moves:
		if moves[move] == 0: #if this move does no damage
			continue
		newhistory = list(history)
		newhistory.append(move)
		simulate_scenarios(destination, hp - moves[move], moves, funct, newhistory)
	return destination

#-----------------------------------CLASSES-----------------------------------------

class Player:
	def __init__(self):
		self.pokemons = []
		self.items = []

	def move(self, location):
		BASE_URL = "https://www.pokemon-vortex.com/"
		if driver.current_url == BASE_URL + location:
			return
		driver.get(BASE_URL + location)

	def login(self):
		config = open("config", "r")
		username, password = config.read().split('\n')
		driver.get("https://www.pokemon-vortex.com/login/")
		username_field = driver.find_element_by_id("myusername")
		password_field = driver.find_element_by_id("mypassword")
		login_button = driver.find_element_by_id("submit")

		username_field.send_keys(username)
		password_field.send_keys(password)
		login_button.send_keys(Keys.RETURN)

	def gotta_catch_em_all(self):
		global found
		self.move('map/live')
		found = False
		mutex = Lock()
		pokefound = Lock()
		thread = Thread(target=check_pokemon_name, args=(mutex,pokefound,))
		thread.start()
		#find_pokemon
		offset = 0
		while (True):
			pokefound.acquire(1)
			if found == True:
				pokefound.release()
				break
			pokefound.release()
			left_interval = random.randrange(10,35)
			holdKey(driver, pokefound, (offset + left_interval) / 100, "D")
			offset = left_interval
			right_interval = random.randrange(10,35)
			holdKey(driver, pokefound, (offset + right_interval) / 100, "A")
			offset = right_interval

	def init_team(self):
		self.move('team')
		cards_group = driver.find_element(by=By.CLASS_NAME, value="cards-group")
		raw_data = cards_group.text.split('\n')
		info = [raw_data[x:x+9] for x in range(0, len(raw_data), 9)]
		for i in range(len(info)):
			self.pokemons.append(Pokemon(info[i][0], info[i][1], "", info[i][5:9]))

	def sidequest(self):
		self.move('battle-sidequest/1')

		battle = Battle(self.pokemons) #initializes the battle
		for enemy in battle.enemies: #loop over all enemies
			ally, moveset = battle.ally_pokemon_choice(self.pokemons, enemy, target_sidequest_reached)
			print(ally.name)
			print(moveset)
			break

	def catch(self):
		driver.find_element(by=By.TAG_NAME, value="body").send_keys(Keys.SPACE)

		battle = Battle(self.pokemons) #initializes the battle
		for enemy in battle.enemies: #loop over all enemies
			ally, moveset = battle.ally_pokemon_choice(self.pokemons, enemy, target_catchable_reached)
			if not ally:
				print("No possible moveset could be found")
				break
			print(ally.name)
			print(moveset)
			break

class Battle:
	def __init__(self, allies):
		time.sleep(0.5)
		self.allies = allies
		self.enemies = [Pokemon()] * 6
		#init enemies
		raw_data = driver.find_element(by=By.ID, value="opponentPoke").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i in range(len(info)):
			self.enemies[i] = Pokemon(info[i][0], info[i][1], info[i][2])
		#init allies
		raw_data = driver.find_element(by=By.ID, value="pokeChoose").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i, pokemon in enumerate(self.allies):
			pokemon.hp = int(info[i][2].split(' ')[-1])

	def ally_pokemon_choice(self,allies, enemy, funct):
		simulation = [[] for _ in range(len(allies))]
		for i, pokemon in enumerate(allies): #all remaining allies
			if pokemon.hp <= 0:
				continue
			move_dmg = dict()
			for move in pokemon.moves: #get effective damage against enemy
				move_dmg[move] = pokemon.moves[move].raw_damage * get_type_multiplier(pokemon.moves[move].type, enemy.types)
				if enemy.special == "metallic":
					move_dmg[move] *= 0.75
				move_dmg[move] /= 60
			simulate_scenarios(simulation[i], enemy.hp, move_dmg, funct)
		best_pokemon = None
		best_scenario = None
		for i, simulate in enumerate(simulation):
			if not simulate:
				continue
#			print(simulate)
			for scenario in simulate:
				if best_scenario == None or len(best_scenario) > len(scenario):
					best_scenario = scenario
					best_pokemon = allies[i]
		return (best_pokemon, best_scenario)

class Item:
	def __init__(self):
		self.name = ""
		self.quantity = 0

class Pokemon:
	def __init__(self, name="", level="", hp="", moves=[]):
		self.special = ""
		self.moves = dict()
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
			self.types = pokedb[self.name].types
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
				move_name = move.replace(' ', '-').lower()
				self.moves[move_name] = Move(move_name)
			for move in self.moves:
				same_type_attack_bonus = 1.5 if self.moves[move].type in self.types else 1
				self.moves[move].raw_damage = self.level * self.moves[move].power * same_type_attack_bonus
				if self.special == "dark":
					self.moves[move].raw_damage *= 1.25

class Move:
	def __init__(self, name = ""):
		self.name = name
		self.type = ""
		self.power = 0
		self.damage = None
		if name != "":
			self.type, self.power = move_library[name]
#			print (self.name, self.type, self.power)
#------------------------------------------------------------------------------------

#log = open("log_" + datetime.now().strftime("%d-%m-%Y_%H-%M"), "w+")


player = Player()
player.login()
player.move('team')
player.init_team()
player.gotta_catch_em_all()
#player.move('map/live')
player.catch()
#player.move('map/live')
#player.sidequest()
quit()
#------------------------------------LOOP-----------------------------------