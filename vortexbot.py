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
try:
	names = config['desired_pokemon']
	if names == []:
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

found = False

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

def hp_reached_target(hp, target_range):
	return True if hp >= target_range[0] and hp <= target_range[1] else False

def is_last_enemy(count, enemies):
	return True if count == 5 or enemies[count + 1].name == "" else False

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

#Get the name of the current encountered pokemon and see if it matches the list of pokemon we're looking to catch
def check_pokemon_name(mutex, pokefound):
	last_pokemon = ""
	global found
#	global log
	time.sleep(1)
	while True:
		mutex.acquire(1)
		driver.execute_script('document.querySelector("#logout").text = Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.pokeName._text')
		pokeName = driver.find_element(by=By.ID, value="logout").get_attribute("text")
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
		if enemy.special == "metallic":
			move_dmg[move] *= 0.75
		move_dmg[move] /= 60
		move_dmg[move] = int(move_dmg[move])
	return (move_dmg)

#Recursively checks all combinations of moves to see if they eventually lead to the enemy hp reaching target_range (defined by FightType)
def simulate_scenarios(destination, enemy, pokemon, moves, target_range, history=[]):
	if enemy.hp >= target_range[0] and enemy.hp <= target_range[1]:
		return destination.append(history)
	if enemy.hp <= 0 or (history and len(history) >= 8):
		return
	for move in moves:
		new_enemy = copy.deepcopy(enemy)
		if history != [] and enemy.name == "ditto":
			new_enemy.types = pokemon.types
			new_enemy.name = pokemon.name
			new_enemy.special = pokemon.special
			moves = get_moves_finaldmg(pokemon, new_enemy)
		if moves[move] == 0:
			continue
		newhistory = list(history)
		newhistory.append(move)
		new_enemy.hp -= moves[move]
		simulate_scenarios(destination, new_enemy, pokemon, moves, target_range, newhistory)
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

	#Necessary for fighting/catching pokemon, all damage is calculated from this information
	def init_team(self):
		self.move('team')
		cards_group = driver.find_element(by=By.CLASS_NAME, value="cards-group")
		raw_data = cards_group.text.split('\n')
		info = [raw_data[x:x+9] for x in range(0, len(raw_data), 9)]
		for i in range(len(info)):
			self.pokemons.append(Pokemon(info[i][0], info[i][1], "", info[i][5:9]))

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
			while self.fight(Trainer(), 10) != True:
				driver.get(GYM_BASE_URL + gym)
		print("You have beaten all the (remaining) gyms!")

	#Completes a 'fight', fight is classified as 6 allies and 1-6 enemies
	#If the hp of the last enemy has reached the target (defined by the FightType) the function will return True
	#If all allies have died and the enemy hasn't reached it's target, the function will return False
	def fight(self, fighttype, minimum_duration=0):
		battle = Battle(self.pokemons, fighttype)
		minimum_endtime = time.time() + minimum_duration
		for count, enemy in enumerate(battle.enemies):
			if enemy.name == "":
				return True
			for _ in range(len(self.pokemons)):
				pokeslot, moveset = battle.ally_pokemon_choice(self.pokemons, enemy, battle.fighttype.target_range)
				if pokeslot == -1:
					print("No valid option could be found")
					return False
				print("Pokeslot:", pokeslot + 1)
				print(moveset)
				battle.fighttype.select_ally(pokeslot)
				for move in moveset:
					while True:
						if battle.attack(enemy, pokeslot, move) == True or battle.allies[pokeslot].hp == 0:
							break
					if battle.allies[pokeslot].hp <= 0 or hp_reached_target(enemy.hp, battle.fighttype.target_range):
						finish_loading()
						if hp_reached_target(enemy.hp, battle.fighttype.target_range) and is_last_enemy(count, battle.enemies):
							while time.time() < minimum_endtime:
								time.sleep(0.3)
							battle.continue_button()
							return True
						battle.continue_button()
						finish_loading()
						break
				if hp_reached_target(enemy.hp, battle.fighttype.target_range):
					break
		return False

	def sidequest_loop(self):
		sidequest_count = 0
		start_time = datetime.now()
		while True:
			try:
				if player.sidequest() == True:
					sidequest_count += 1
					print ("Sidequest #", sidequest_count, sep="")
					elapsed = datetime.now() - start_time
					minutes = divmod(int(elapsed.seconds), 60)
					print(minutes[0], ":", minutes[1], sep="")
			except TimeoutException:
				pass

	def sidequest(self):
		driver.get('https://www.pokemon-vortex.com/battle-sidequest/1')
		if driver.current_url == "https://www.pokemon-vortex.com/sidequests/":
			driver.find_element(by=By.XPATH, value='//*[@id="ajax"]/div[2]/form/button').click()
			reward = locateElement(driver, By.XPATH, '//*[@id="ajax"]/div[1]/b').text
			with open('reward_' + datetime.now().strftime("%d-%m-%Y_%H-%M"), 'w+') as f:
				f.write(reward)
			print(reward)
			print("Sidequest reward received!")
			time.sleep(5)
			driver.get('https://www.pokemon-vortex.com/battle-sidequest/1')
		try:
			driver.find_element(by=By.XPATH, value="//*[text()='An error occurred with the sidequest battle you requested.']")
			driver.find_element(by=By.XPATH, value="//*[text()='An error has occurred. Please try again later.']")
			print("Looks like you've reached the end of the sidequests, will reset now!")
			self.reset_sidequests()
			return False
		except:
			pass
		return self.fight(Trainer(), 10)

	def catch(self):
		driver.find_element(by=By.TAG_NAME, value="body").send_keys(Keys.SPACE)
		self.fight(WildEncounter())

#Class that defines a way of interacting with the UI for a given scenario, and also provides a target_range used to work out a desired moveset
class FightType:
	def __init__(self, target_range):
		self.target_range = target_range

#Used for lowering pokemon to catch them
class WildEncounter(FightType):
	def __init__(self):
		super().__init__((1, 30))

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
		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input[10]').submit()
		finish_loading()

	def update_hp(self, enemy, ally):
		enemy.hp = int(locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/table/tbody/tr[1]/td[1]/strong').text.split(' ')[1])
		ally.hp = int(locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/table/tbody/tr[2]/td[2]/strong').text.split(' ')[1])

	def continue_button(self):
		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input').submit()

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

#Holds the data needed for a battle, enemies and hp primarily.
class Battle:
	def __init__(self, allies, FightType):
		self.allies = allies
		self.enemies = [Pokemon()] * 6
		self.fighttype = FightType
		#init enemies
		raw_data = locateElement(driver, By.ID, "opponentPoke").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i in range(len(info)):
			self.enemies[i] = Pokemon(info[i][0], info[i][1], info[i][2])
		#init allies
		raw_data = driver.find_element(by=By.ID, value="pokeChoose").text.split('\n')
		info = [raw_data[i:i+3] for i in range (0, len(raw_data), 3)]
		for i, pokemon in enumerate(self.allies):
			pokemon.hp = int(info[i][2].split(' ')[-1])

	def continue_button(self):
		self.fighttype.continue_button()

	#bug: if enemy is burned/taking DOT, this will return True, causing the battle to time out
	def attack(self, enemy, pokeslot, move):
		hp_before = enemy.hp
		self.fighttype.attack(move)
		self.fighttype.update_hp(enemy, self.allies[pokeslot])
		return True if hp_before != enemy.hp else False

	def ally_pokemon_choice(self,allies, enemy, target_range):
		simulation = [[] for _ in range(len(allies))]
		for i, pokemon in enumerate(allies):
			if pokemon.hp <= 0:
				continue
			move_dmg = get_moves_finaldmg(pokemon, enemy)
			simulate_scenarios(simulation[i], copy.deepcopy(enemy), pokemon, move_dmg, target_range)
		best_pokemon = -1
		best_scenario = None
		for i, simulate in enumerate(simulation):
			if not simulate:
				continue
			for scenario in simulate:
				if best_scenario == None or len(best_scenario) > len(scenario):
					best_scenario = scenario
					best_pokemon = i
		return (best_pokemon, best_scenario)

class Pokemon:
	def __init__(self, name="", level="", hp="", moves=[]):
		self.special = ""
		self.moves = dict()
		self.types = []
		if not name:
			self.name = ""
		else:
			fullname = re.sub(r'[\(\.\'\)]', '', name.lower()).split(' ')
			if fullname[0] in ["metallic","shiny","shadow","mystic","dark","pink","crystal","ancient"]:
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
				move_name = move
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
