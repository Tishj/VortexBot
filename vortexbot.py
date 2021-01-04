from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By
from datetime import datetime
from enum import Enum

from threading import Thread, Lock
import json, time, random, sys, os
import re
import pickle
import copy
import yaml

#--------------------------------------INCLUDES--------------------------------------

sidequest_number = 0
last_battle_won = time.time() - 10

try:
	with open('config.yml', 'r') as f:
		config = yaml.load(f)
except:
	print("Your config.yml is either missing or corrupted, please make sure there's a valid config.yml in the current folder")

#Load the databases
try:
	with open('movedb', 'rb') as f:
		move_library = pickle.load(f)
	with open('pokedb', 'rb') as f:
		pokedb = pickle.load(f)
	with open('multiplierdb', 'rb') as f:
		multipliers = pickle.load(f)
except:
	print("Looks like one or more of the databases/dictionaries needed to run the bot is outdated, please rerun the required update scripts and try again")
	quit()

#Variables used by the pokemon catching/finding functions
criteria = dict()
try:
	criteria['names'] = config['desired_pokemon']
	if criteria['names'] == []:
		raise Exception("Desired pokemon list empty")
except:
	print("Desired pokemon list is missing or empty")
	try:
		if config['mode'] == "catch":
			print ("Cant catch with an empty desired pokemon list, if you meant to catch any pokemon, add \"\" to the desired_pokemon list")
			quit()
	except:
		print("Mode missing")
		quit()

found = None

#Selenium set up
PATH = "./req/chromedriver.exe"
driver = webdriver.Chrome(service=Service(PATH))

#-------------------------------FUNCTIONS---------------------------------------------

#Uses selenium webdriver to find an element, waiting until at most 'timeout' seconds to find it
def locateElement(driver, by, value, timeout=10):
	ignored_exceptions = (NoSuchElementException,StaleElementReferenceException,)
	wait = WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions)
	return wait.until(ec.visibility_of_element_located((by, value)))

#Waits for the 'loading ..' element to disappear
def finish_loading():
	while True:
		loading_element = driver.find_element(By.XPATH, '//*[@id="loading"]')
		if "visibility: hidden" in loading_element.get_attribute("style") or loading_element.get_attribute("style") == None:
			break

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
		if time.time() > endtime or found != None:
			dispatchKeyEvent(driver, "keyUp", options)
			pokefound.release()
			break
		pokefound.release()
		options["autoRepeat"] = True
		time.sleep(0.01)

def evaluate_pokemon_info(mutex, pokefound, last_pokemon):
	global found
	global criteria
	try:
		mutex.acquire(1)
		driver.execute_script('document.querySelector("#logout").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeName._text')
		driver.execute_script('document.querySelector("#battleTab > a").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.caughtImg._alpha')
		driver.execute_script('document.querySelector("#yourAccountTab > a").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeLvl._text')
		pokeName = driver.find_element(by=By.ID, value="logout").get_attribute("text")
		pokeCaught = bool(int())
		result = driver.find_element(by=By.XPATH, value='//*[@id="yourAccountTab"]/a').get_attribute('text')
		pokeLvl = 0 if result == "" else int(result.split(' ')[1])
		result = driver.find_element(by=By.XPATH, value='//*[@id="battleTab"]/a').get_attribute('text')
		pokeCaught = bool(int(result)) if pokeLvl != 0 else True
		mutex.release()
	except:
		print("Name checker has encountered a fatal error")
		os._exit(1)
#	if criteria.has_key('')
	if pokeLvl != 0 and pokeName != None and pokeName != last_pokemon:
		for name in criteria['names']:
			if name in pokeName:
				pokefound.acquire(1)
				found = (pokeName, pokeLvl, pokeCaught)
				pokefound.release()
				return True
	last_pokemon[0] = pokeName
	return False

#Get the name of the current encountered pokemon and see if it matches the list of pokemon we're looking to catch
def check_pokemon_name(mutex, pokefound):
	last_pokemon = ""
	wrapper = [last_pokemon]
	while True:
		if evaluate_pokemon_info(mutex, pokefound, wrapper):
			return
		print(wrapper[0])
		time.sleep(1)

#Return the type multiplier based of the move's type and the enemy type(s)
def get_type_multiplier(dmgtype, enemy_types):
	mult = 1
	for enemy_type in enemy_types:
		if multipliers[dmgtype][enemy_type] == 0:
			return 0
		mult *= multipliers[dmgtype][enemy_type]
	return mult

#Based on the enemy, determine the damage each move is going to do against said enemy
def get_moves_finaldmg(pokemon, enemy):
	move_dmg = dict()
	for move in pokemon.moves:
		move_dmg[move] = pokemon.moves[move].raw_damage * get_type_multiplier(pokemon.moves[move].type, enemy.types)
		if enemy.special == "Metallic":
			move_dmg[move] *= 0.75
		move_dmg[move] /= 60
		move_dmg[move] = int(move_dmg[move])
	return (move_dmg)

#Recursively checks all combinations of moves to see if they eventually lead to the enemy hp reaching target_range (defined by FightType)
def simulate_scenarios(destination, enemy, pokemon, target_range, history=[]):
	if enemy.hp >= target_range[0] and enemy.hp <= target_range[1]:
		return destination.append(history)
	if enemy.hp <= 0 or (history and len(history) >= 8):
		return
	for move in pokemon.moves:
		new_enemy = copy.deepcopy(enemy)
		if history != [] and enemy.name == "Ditto":
			new_enemy.types = pokemon.types
			new_enemy.name = pokemon.name
			new_enemy.special = pokemon.special
			pokemon.set_movesdmg(enemy)
		if pokemon.moves[move].damage == 0:
			continue
		newhistory = list(history)
		newhistory.append(move)
		new_enemy.hp -= pokemon.moves[move].damage
		simulate_scenarios(destination, new_enemy, pokemon, target_range, newhistory)
	return destination

#-----------------------------------CLASSES-----------------------------------------

class Player:
	def __init__(self):
		self.pokemons = []
		self.items = {}

	def move(self, location):
		BASE_URL = "https://www.pokemon-vortex.com/"
		if driver.current_url == BASE_URL + location:
			return
		driver.get(BASE_URL + location)

	def login(self):
		global config
		try:
			username = config['player']['username']
			password = config['player']['password']
			if not (username or password):
				raise Exception("Empty username or password")
		except:
			print("Your config.yml does not contain a 'username' or 'password' field, or they are empty")
			quit()

		driver.get("https://www.pokemon-vortex.com/login/")
		username_field = driver.find_element(by=By.ID, value="myusername")
		password_field = driver.find_element(by=By.ID, value="mypassword")
		login_button = driver.find_element(by=By.ID, value="submit")

		username_field.send_keys(username)
		password_field.send_keys(password)
		login_button.send_keys(Keys.RETURN)

	#Running this will reset your sidequest progress, happens automatically at 2121 (the final sidequest at the time of writing)
	def reset_sidequests(self):
		locateElement(driver, By.XPATH, '//*[@id="optionsTab"]').click()
		locateElement(driver, By.XPATH, '//*[@id="enableSqReset"]').click()
		locateElement(driver, By.XPATH, '//*[@id="sqReset"]').click()

	#The goal of this function is to walk around the map until a pokemon is encountered that matches the list of desired_pokemon
	def gotta_catch_em_all(self):
		#log = open("log_" + datetime.now().strftime("%d-%m-%Y_%H-%M"), "w+")
		global found
		self.move('map/live')
		locateElement(driver, By.XPATH, '//*[@id="mapapp"]')
		found = None
		mutex = Lock()
		pokefound = Lock()
		time.sleep(4)
		if evaluate_pokemon_info(mutex, pokefound, [""]):
			return
		thread = Thread(target=check_pokemon_name, args=(mutex,pokefound,))
		thread.start()
		#find_pokemon
		offset = 0
		while (True):
			pokefound.acquire(1)
			if found != None:
				pokefound.release()
				break
			pokefound.release()
			left_interval = random.randrange(10,35)
			holdKey(driver, pokefound, (offset + left_interval) / 100, "D")
			offset = left_interval
			right_interval = random.randrange(10,35)
			holdKey(driver, pokefound, (offset + right_interval) / 100, "A")
			offset = right_interval
		print("Going to catch a Level", found[1], found[0], "that I", ("have" if found[2] else "havent"), "caught before!")

	#Necessary for fighting/catching pokemon, all damage is calculated from this information
	def init_team(self):
		self.move('team')
		cards_group = driver.find_element(by=By.CLASS_NAME, value="cards-group")
		raw_data = cards_group.text.split('\n')
		info = [raw_data[x:x+9] for x in range(0, len(raw_data), 9)]
		for i in range(len(info)):
			self.pokemons.append(Pokemon(info[i][0], info[i][1], "", info[i][5:9], i))

	def gyms(self, only_unobtained=True):
		GYM_BASE_URL = "https://www.pokemon-vortex.com/battle-gym/"

		if only_unobtained:
			driver.get('https://www.pokemon-vortex.com/gyms/')
			notdone = driver.find_elements(by=By.XPATH, value='//*[@class="notDone"]/../..')
			todo = [item.get_attribute('text')[:-1] for item in notdone if item.get_attribute('text') != None]
		else:
			todo = [
			"Brock", "Misty", "Lt. Surge", "Erika", "Sabrina", "Janine", "Blaine", 
			"Giovanni", "Cissy", "Danny", "Rudy", "Luana", "Drake", "Falkner", "Bugsy", 
			"Whitney", "Morty", "Chuck", "Jasmine", "Pryce", "Clair", "Roxanne",
			"Brawly", "Wattson", "Flannery", "Norman", "Winona", "Liza and Tate", "Juan", 
			"Roark", "Gardenia", "Maylene", "Crasher Wake", "Fantina", "Byron", 
			"Candice", "Volkner", "Cheren", "Roxie", "Burgh", "Elesa", "Clay", "Skyla", 
			"Drayden", "Marlon", "Viola", "Grant", "Korrina", "Ramos", "Clemont", "Valerie", 
			"Olympia", "Wulfric", "Ilima", "Lana", "Kiawe", "Mallow", "Sophocles", "Acerola", 
			"Mina", "Hala", "Olivia", "Nanu", "Hapu"]

		if todo == []:
			print("You have obtained all gym badges already, try calling gyms with 'only_unobtained=False'")
			quit()
		for gym in todo:
			driver.get(GYM_BASE_URL + gym)
			battle = Battle(self.pokemons, Trainer())
			while battle.fight(10) != True:
				driver.get(GYM_BASE_URL + gym)
		print("You have beaten all the (remaining) gyms!")

	def sidequest_loop(self):
		global sidequest_number
		driver.get('https://www.pokemon-vortex.com/sidequests/')
		sidequest_number = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/div[1]/p[2]/b').text)
		start_time = datetime.now()
		while True:
			try:
				if player.sidequest() == True:
					sidequest_number += 1
					print ("Sidequest #", sidequest_number, sep="")
					elapsed = datetime.now() - start_time
					minutes = divmod(int(elapsed.seconds), 60)
					print(minutes[0], ":", minutes[1], sep="")
			except TimeoutException:
				pass

	def sidequest(self):
		global sidequest_number
		driver.get('https://www.pokemon-vortex.com/battle-sidequest/' + str(sidequest_number + 1))
		if driver.current_url == "https://www.pokemon-vortex.com/sidequests/":
			driver.find_element(by=By.XPATH, value='//*[@id="ajax"]/div[2]/form/button').click()
			reward = locateElement(driver, By.XPATH, '//*[@id="ajax"]/div[1]/b').text
			with open('reward_' + datetime.now().strftime("%d-%m-%Y_%H-%M"), 'w+') as f:
				f.write(reward)
			print(reward)
			print("Sidequest reward received!")
			time.sleep(5)
			driver.get('https://www.pokemon-vortex.com/battle-sidequest/' + str(sidequest_number + 1))
		try:
			driver.find_element(by=By.XPATH, value="//*[text()='An error occurred with the sidequest battle you requested.']")
			driver.find_element(by=By.XPATH, value="//*[text()='An error has occurred. Please try again later.']")
			print("Looks like you've reached the end of the sidequests, will reset now!")
			self.reset_sidequests()
			sidequest_number = 0
			return False
		except:
			pass
		battle = Battle(self.pokemons, Trainer())
		return battle.fight(10)

	def catch(self):
		if driver.current_url != "https://www.pokemon-vortex.com/map/live":
			return print("Cant run 'catch' when you're not on the map!") #throw exception??
		if found == None and evaluate_pokemon_info(Lock(), Lock(), [""]) == False:
			return print("No pokemon was found, run 'gotta_catch_em_all' first")
		driver.find_element(by=By.TAG_NAME, value="body").send_keys(Keys.SPACE)
		level = found[1]
		if level < 15:
			max_hp = 10
		elif level < 30:
			max_hp = 20
		else:
			max_hp = 30
		battle = Battle(self.pokemons, WildEncounter((1,max_hp)))
		if battle.fight() == False:
			return print("Failed to lower the pokemon enough to capture it")
#		if battle.catch() == False:
#			print("Failed to catch the wild pokemon")
		#if "The wild Pokémon has been caught." in //*[@id="battleForm"]/div/div/strong[2].text:

#Class that defines a way of interacting with the UI for a given scenario, and also provides a target_range used to work out a desired moveset
class FightType:
	def __init__(self, target_range):
		self.target_range = target_range

#Used for lowering pokemon to catch them
class WildEncounter(FightType):
	def __init__(self, target_range=(1,30)):
		super().__init__(target_range)

	def select_ally(self, pokeslot):
		row, col = divmod(pokeslot, 3)
		row += 1
		col += 1
		locateElement(driver, By.XPATH, "//*[@id=\"pokeChoose\"]/tbody/tr[" + str(row) + "]/td[" + str(col) + "]/label/div").click()
		locateElement(driver, By.XPATH, '//*[@id="ajax"]/form/p/input').submit()

	def attack(self, move):
		finish_loading()
		locateElement(driver, By.XPATH, "//label[contains(., '" + move + "')]").click()
		finish_loading()
		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input[@type="submit"]').submit()
#		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input[10]').submit()
		finish_loading()

	def update_hp(self, enemy, ally):
		enemy.hp = int(locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/table/tbody/tr[1]/td[1]/strong').text.split(' ')[1])
		ally.hp = int(locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/table/tbody/tr[2]/td[2]/strong').text.split(' ')[1])

	def continue_button(self):
		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input').submit()

	def get_moveset(self, battle, enemy):
		simulation = [[] for _ in range(len(battle.allies))]
		for i, pokemon in enumerate(battle.allies):
			if pokemon.hp <= 0:
				continue
#			move_dmg = get_moves_finaldmg(pokemon, enemy)
			pokemon.set_movesdmg(enemy)
			simulate_scenarios(simulation[i], copy.deepcopy(enemy), pokemon, battle.target_range)
		best_pokemon = None
		best_scenario = None
		for i, simulate in enumerate(simulation):
			if not simulate:
				continue
			for scenario in simulate:
				if best_scenario == None or len(best_scenario) > len(scenario):
					best_scenario = scenario
					best_pokemon = i
		battle.current_ally = battle.allies[best_pokemon]
		return (best_scenario)

#Used in sidequest battles and other trainer battles, the goal is to kill the enemy pokemon (target_range(-5000, 0))
class Trainer(FightType):
	def __init__(self):
		super().__init__((-5000, 0))

	def select_ally(self, pokeslot):
		locateElement(driver, By.XPATH, "//*[@id='slot" + str(int(pokeslot) + 1) + "']/label/div").click()
		locateElement(driver, By.XPATH, '//*[@id="ajax"]/form/p/input').submit()

	def attack(self, move):
		finish_loading()
		locateElement(driver, By.XPATH, "//label[contains(., '" + move + "')]").click()
		finish_loading()
		locateElement(driver, By.XPATH, '//*[@id="ajax"]/form[2]/div/input[2]').submit()
		finish_loading()

	def update_hp(self, enemy, ally):
		enemy.hp = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/form[2]/div/table[1]/tbody/tr[1]/td[1]/strong').text.split(' ')[1])
		ally.hp = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/form[2]/div/table[1]/tbody/tr[2]/td[2]/strong').text.split(' ')[1])

	def continue_button(self):
		locateElement(driver, By.XPATH, '//*[@id="ajax"]/form[2]/div/input[2]').submit()

	def get_moveset(self, battle, enemy):
		strongest_move = None
		for ally in [x for x in battle.allies if not x.dead()]:
			ally.set_movesdmg(enemy)
			for move in ally.moves:
				if strongest_move == None or ally.moves[move].damage > strongest_move.damage:
					strongest_move = ally.moves[move]
					battle.current_ally = ally
				if strongest_move.damage >= enemy.hp:
					break ;
			if strongest_move.damage >= enemy.hp:
				break ;
		if strongest_move == None:
			return []
		return [strongest_move.name] * int((enemy.hp / strongest_move.damage) + 1)

#Holds the data needed for a battle, enemies and hp primarily.
class Battle:
	#initialize enemy hp and ally hp
	def __init__(self, allies, FightType):
		self.allies = allies
		self.fighttype = FightType
		self.current_ally = None
		self.enemies = []
		self.target_range = FightType.target_range
		#init enemies
		raw_data = locateElement(driver, By.ID, "opponentPoke").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i in range(len(info)):
			self.enemies.append(Pokemon(info[i][0], info[i][1], info[i][2], [], i))
		#init allies
		raw_data = driver.find_element(by=By.ID, value="pokeChoose").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i, pokemon in enumerate(self.allies):
			pokemon.level = int(info[i][1].split(' ')[-1])
			pokemon.hp = int(info[i][2].split(' ')[-1])
		self.current_enemy = 0

	def continue_button(self):
		self.fighttype.continue_button()
	def select_ally(self):
		self.fighttype.select_ally(self.current_ally.slot)
	def last_enemy(self):
		return True if self.current_enemy + 1 == len(self.enemies) else False

	#Completes a 'fight', fight is classified as 6 allies and 1-6 enemies
	#If the hp of the last enemy has reached the target (defined by the FightType) the function will return True
	#If all allies have died and the enemy hasn't reached it's target, the function will return False
	def fight(self, minimum_duration=0):
		global last_battle_won
		while self.current_enemy < len(self.enemies):
			enemy = self.enemies[self.current_enemy]
			for _ in range(len([x for x in self.allies if not x.dead()])): #loop over all living allies
#				moveset = self.ally_pokemon_choice(enemy)
				moveset = self.fighttype.get_moveset(self,enemy)
				if not self.current_ally:
					print("No valid option could be found")
					return False
#				print("Current ally:", self.current_ally.name, "slot:", self.current_ally.slot)
#				print(moveset)
				self.select_ally()
				for move in moveset:
					while True:
						if self.attack(move) == True or self.current_ally.dead():
							break
					if self.current_ally.dead() or enemy.hp_in_range(self.target_range):
						finish_loading()
						if enemy.hp_in_range(self.target_range) and self.last_enemy():
							while time.time() < last_battle_won + minimum_duration:
								time.sleep(0.3)
							self.continue_button()
							last_battle_won = time.time()
							return True
						self.continue_button()
						finish_loading()
						break
				if enemy.hp_in_range(self.target_range):
					self.current_enemy += 1
					break
		return False

	#bug: if enemy is burned/taking DOT, this will return True, causing the battle to time out
	#ditto is still going to break my new system for the first move
	def attack(self, move):
		enemy = self.enemies[self.current_enemy]
		hp_before = enemy.hp
		self.fighttype.attack(move)
		self.fighttype.update_hp(enemy, self.current_ally)
#		print("Damage of current move:", self.current_ally.moves[move].damage)
#		print("HP before:", hp_before, "HP after:", enemy.hp, "difference:", hp_before - enemy.hp)
		return True if (enemy.hp == 0 or hp_before - enemy.hp >= self.current_ally.moves[move].damage) else False

	#update_current_ally
	def ally_pokemon_choice(self, enemy):
		simulation = [[] for _ in range(len(self.allies))]
		for i, pokemon in enumerate(self.allies):
			if pokemon.hp <= 0:
				continue
#			move_dmg = get_moves_finaldmg(pokemon, enemy)
			pokemon.set_movesdmg(enemy)
			simulate_scenarios(simulation[i], copy.deepcopy(enemy), pokemon, self.target_range)
		best_pokemon = None
		best_scenario = None
		for i, simulate in enumerate(simulation):
			if not simulate:
				continue
			for scenario in simulate:
				if best_scenario == None or len(best_scenario) > len(scenario):
					best_scenario = scenario
					best_pokemon = i
		self.current_ally = self.allies[best_pokemon]
		return (best_scenario)

class Pokemon:
	def __init__(self, name="", level="", hp="", moves=[], slot=0):
		self.special = ""
		self.moves = dict()
		self.types = []
		self.slot = slot
		if not name:
			self.name = ""
		else:
			fullname = name.split(' ')
			if fullname[0] in ["Metallic","Shiny","Shadow","Mystic","Dark","Pink","Crystal","Ancient"]:
				self.special = fullname[0]
				self.name = " ".join(fullname[1:]) 
			else:
				self.name = " ".join(fullname)
			self.types = pokedb[self.name].types
		self.level = 0 if not level else int(level.split(' ')[-1])
		self.hp = -1 if not hp else int(hp.split(' ')[-1])
		if moves:
			for move in moves:
				self.moves[move] = Move(move, self)
			# for move in self.moves:
			# 	same_type_attack_bonus = 1.5 if self.moves[move].type in self.types else 1
			# 	self.moves[move].raw_damage = self.level * self.moves[move].power * same_type_attack_bonus
			# 	if self.special == "Dark":
			# 		self.moves[move].raw_damage *= 1.25

	def dead(self):
		return True if self.hp <= 0 else False
	def hp_in_range(self, range):
		return True if self.hp >= range[0] and self.hp <= range[1] else False
	def set_movesdmg(self, enemy):
		for move in self.moves:
			self.moves[move].set_damage(enemy)

class Move:
	def __init__(self, name = "", pokemon = None):
		self.name = name
		self.type = ""
		self.power = 0
		self.basedmg = 0
		self.damage = 0
		if name != "":
			self.type, self.power = move_library[name]
		if pokemon != None:
			self.basedmg = pokemon.level * self.power * (1.5 if self.type in pokemon.types else 1) * (1.25 if pokemon.special == "Dark" else 1)
#			print(self.name, "=", pokemon.level, self.power, "(", self.type, pokemon.types, ")", pokemon.special)
#			print(self.basedmg)

	def get_multiplier(self, enemy_types):
		mult = 1
		for enemy_type in enemy_types:
			if multipliers[self.type][enemy_type] == 0:
				return 0
			mult *= multipliers[self.type][enemy_type]
		return mult

	def set_damage(self, enemy):
		self.damage = int((self.basedmg * self.get_multiplier(enemy.types) * (0.75 if enemy.special == "Metallic" else 1)) / 60)

#---------------------------------------MAIN----------------------------------------

player = Player()
player.login()
player.init_team()

if config['mode'] == "catch":
	player.gotta_catch_em_all()
	player.catch()
elif config['mode'] == "sidequest":
	player.sidequest_loop()
elif config['mode'] == "gyms":
	player.gyms()
#else if config['mode'] == "clanbattle"
#	player.clanbattle_loop
