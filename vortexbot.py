from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import logging

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

#load config
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
	criteria['pokemon'] = config['pokemon']
	if not criteria['pokemon']:
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

def get_platform():
	platforms = {
		'linux1' : 'Linux',
		'linux2' : 'Linux',
		'darwin' : 'OS X',
		'win32' : 'Windows',
		'linux' : 'Windows'
	}
	if sys.platform not in platforms:
		print("OS not supported!", sys.platform)
		return sys.platform

	return platforms[sys.platform]

#Selenium set up
PATH = "./req/chromedriver.exe"
platform = get_platform()
if platform == "Windows":
	PATH = "./req/chromedriver.exe"
else:
	PATH = "./req/chromedriver"

desired = DesiredCapabilities.CHROME
desired['goog:loggingPrefs'] = { 'browser':'ALL' }
driver = webdriver.Chrome(service=Service(PATH), desired_capabilities=desired)

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

def selector_met(selection_group, key, ppty):
	return True if key not in selection_group or ppty in selection_group[key] else False

def meets_criteria(encounter):
	global criteria
	if not criteria['pokemon'][encounter.rarity]:
		print(encounter.rarity, 'selection groups for this rarity are empty')
		return True
	if encounter.rarity not in criteria['pokemon']:
		print("RARITY '", encounter.rarity, "' missing from config!")
		os._exit(1)
	for selection_group in criteria['pokemon'][encounter.rarity]:
		if selector_met(criteria['pokemon'][encounter.rarity][selection_group], 'special', encounter.prefix) and selector_met(criteria['pokemon'][encounter.rarity][selection_group], 'caught', encounter.caught) and selector_met(criteria['pokemon'][encounter.rarity][selection_group], 'name', encounter.name):
			print(selection_group, 'Requirements met!', 'with \'caught\':', encounter.caught, 'special:', encounter.prefix, 'name:', encounter.name)
			return True
	return False

def evaluate_pokemon_info(mutex, pokefound, last_pokemon):
	if "UID" not in evaluate_pokemon_info.__dict__: evaluate_pokemon_info.UID = None
	global found
	global criteria
	mutex.acquire(1)
	encounter = driver.execute_script('return Phaser.Display.Canvas.CanvasPool.pool[2].parent.scene.encounterProfile.encounter;')
	mutex.release()
	newUID = None if encounter == None else encounter['id']
	if encounter and newUID and (evaluate_pokemon_info.UID == None or evaluate_pokemon_info.UID != newUID):
		evaluate_pokemon_info.UID = newUID
		pokemon = Encounter()
		pokemon.name = encounter['pokemon']['name']
		pokemon.prefix = encounter['prefix']
		pokemon.level = encounter['level']
		pokemon.caught = encounter['caught']
		pokemon.rarity = encounter['pokemon']['rarity']
		if meets_criteria(pokemon):
			pokefound.acquire(1)
			found = pokemon
			pokefound.release()
			return True
	return False

#Get the name of the current encountered pokemon and see if it matches the list of pokemon we're looking to catch
def check_pokemon_name(mutex, pokefound):
	last_pokemon = ""
	wrapper = [last_pokemon]
	while True:
		if evaluate_pokemon_info(mutex, pokefound, wrapper):
			return
#		print(wrapper[0])
		time.sleep(0.5)

#Return the type multiplier based of the move's type and the enemy type(s)
def get_type_multiplier(dmgtype, enemy_types):
	mult = 1
	for enemy_type in enemy_types:
		if multipliers[dmgtype][enemy_type] == 0:
			return 0
		mult *= multipliers[dmgtype][enemy_type]
	return mult

#Based on the enemy, determine the damage each move is going to do against said enemy
#Might still be fucked, because of dark/metallic mix
def get_moves_finaldmg(pokemon, enemy):
	move_dmg = dict()
	for move in pokemon.moves:
		move_dmg[move] = pokemon.moves[move].raw_damage * get_type_multiplier(pokemon.moves[move].type, enemy.types)
		if enemy.special == "Metallic":
			move_dmg[move] *= 0.75
		move_dmg[move] /= 60
		move_dmg[move] = int(move_dmg[move] + 0.5)
	return (move_dmg)

#Recursively checks all combinations of moves to see if they eventually lead to the enemy hp reaching target_range (defined by FightType)
def simulate_scenarios(destination, enemy, pokemon, target_range, history=[]):
	if enemy.hp >= target_range[0] and enemy.hp <= target_range[1]:
		return destination.append(history)
	if enemy.hp <= 0 or (history and len(history) >= 4):
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

class Encounter:
	def __init__(self, prefix=None, name="", rarity="", level=None, caught=None):
		self.prefix = prefix
		self.name = name
		self.rarity = rarity
		self.level = level
		self.caught = caught

class Player:
	def __init__(self):
		self.pokemons = []
		self.items = { 'Poké Ball' : None, 'Great Ball' : None, 'Ultra Ball' : None }
		self.money = 0

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

	def select_ball_amount(self, ball, amount, total_price):
		types = { 'Poké Ball' : 'poke_ball', 'Great Ball' : 'great_ball', 'Ultra Ball' : 'ultra_ball' }
		prices = { 'Poké Ball' : 250, 'Great Ball' : 800, 'Ultra Ball' : 1500 }
		if amount * prices[ball] > self.money:
			amount = self.money / prices[ball]
		if amount <= 5:
			locateElement(driver, By.XPATH, '//*[@id="' + types[ball] + '_calc"]/option[' + str(amount + 1) + ']').click()
		elif amount <= 10:
			amount = 10
			locateElement(driver, By.XPATH, '//*[@id="' + types[ball] + '_calc"]/option[' + str(7) + ']').click()
		elif amount <= 25:
			amount = 25
			locateElement(driver, By.XPATH, '//*[@id="' + types[ball] + '_calc"]/option[' + str(8) + ']').click()
		elif amount <= 50:
			amount = 50
			locateElement(driver, By.XPATH, '//*[@id="' + types[ball] + '_calc"]/option[' + str(9) + ']').click()
		elif amount <= 100:
			amount = 100
			locateElement(driver, By.XPATH, '//*[@id="' + types[ball] + '_calc"]/option[' + str(10) + ']').click()
		return (amount, prices[ball] * amount);

	#check if we have enough money to buy the pokeballs
	def restock(self):
		driver.get('https://www.pokemon-vortex.com/pokemart/')
		locateElement(driver, By.XPATH, '//*[@id="items-header-balls"]').click()
		total_price = 0
		self.money = int(locateElement(driver, By.XPATH, '//*[@id="yourCash"]').text.replace('You Have: ', '').replace(',', ''))

		balltypes = { 'Poké Ball' : '2', 'Great Ball' : '3', 'Ultra Ball' : '4' }
		balls_purchased = False

		for ball in balltypes:
			if self.items[ball] == None:
				self.items[ball] = int(locateElement(driver, By.XPATH, '//*[@id="items-content-balls"]/tbody/tr[' + balltypes[ball] + ']/td[4]').text)
#			print(ball, "amount:", self.items[ball], "restock:", config['restock'][ball])
			if self.items[ball] < config['restock'][ball]['min']:
				amount, price = self.select_ball_amount(ball, config['restock'][ball]['goal'] - self.items[ball], total_price)
				self.items[ball] += amount
				total_price += price
				balls_purchased = True

		if balls_purchased:
			locateElement(driver, By.XPATH, '//*[@id="checkoutButton"]').click()


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
		time.sleep(4) #replace when I can reliably wait for the map to finish loading
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

	#Necessary for fighting/catching pokemon, all damage is calculated from this information
	def init_team(self):
		self.move('team')
		cards_group = driver.find_element(by=By.CLASS_NAME, value="cards-group")
		raw_data = cards_group.text.split('\n')
		info = [raw_data[x:x+9] for x in range(0, len(raw_data), 9)]
		for i in range(len(info)):
			self.pokemons.append(Pokemon(info[i][0], info[i][1], "", info[i][5:9], i))

	def init_inv(self):
		self.move('inventory')
		locateElement(driver, By.XPATH, '//*[@id="ajax"]/ul/li[2]').click()
		self.items['Poké Ball'] = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/table/tbody/tr[2]/td[4]').text.split(' ')[0])
		self.items['Great Ball'] = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/table/tbody/tr[3]/td[4]').text.split(' ')[0])
		self.items['Ultra Ball'] = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/table/tbody/tr[4]/td[4]').text.split(' ')[0])
		self.items['Master Ball'] = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/table/tbody/tr[9]/td[4]').text.split(' ')[0])
		self.items['Beast Ball'] = int(locateElement(driver, By.XPATH, '//*[@id="ajax"]/table/tbody/tr[11]/td[4]').text.split(' ')[0])

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
		battle.init_hp()
		return battle.fight(10)

	def catch(self):
		global found
		player.move('map/live')
		if found == None and evaluate_pokemon_info(Lock(), Lock(), [""]) == False:
			return print("No pokemon was found, run 'gotta_catch_em_all' first")
		if found.prefix:
			print("Going to catch a Level", found.level, found.prefix, found.name, "that I", ("have" if found.caught else "havent"), "caught before!")
		else:
			print("Going to catch a Level", found.level, found.name, "that I", ("have" if found.caught else "havent"), "caught before!")
		level = found.level
		if level < 15:
			max_hp = 10
		elif level < 30:
			max_hp = 20
		elif level < 75:
			max_hp = 30
		else:
			max_hp = 800
		if level >= 75 and self.items['Beast Ball'] == 0:
			print("No way to catch ultra beast, exiting!")
			quit()
		battle = Battle(self.pokemons, WildEncounter((1,max_hp)))
		enemy = Pokemon(found.name)
		enemy.special = found.prefix
		enemy.level = level
		enemy.hp = level * 4 * (1.25 if "Shiny" in found.prefix else 1)
		for ally in battle.allies:
			ally.hp = ally.level * 4 * (1.25 if "Shiny" in ally.special else 1)
		battle.fighttype.get_moveset(battle, enemy)
		if battle.current_ally == None:
			print("Current team has no way of lowering the enemy to fall within:", battle.target_range[0], "and", battle.target_range[1])
			quit()
			return False
		driver.find_element(by=By.TAG_NAME, value="body").send_keys(Keys.SPACE)
		time.sleep(2) #remove somehow
		battle.init_hp()
		if battle.fight() == False:
			return print("Failed to lower the pokemon enough to capture it")
		finish_loading()
#		battle.fighttype.continue_button()
		if battle.catch(self.items) == False:
			print("Failed to catch the wild pokemon")
		else:
			print("Succesfully captured!")
		found = None

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
#		print("selected", move)
		finish_loading()
		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input[@type="submit"]').submit()
#		print("clicked submit on", move)
#		locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input[10]').submit()
#		self.continue_button()
		finish_loading()

	def update_hp(self, enemy, ally):
#		print('Before: Enemy hp:', enemy.hp, 'Ally hp:', ally.hp)
		enemy.hp = int(locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/table/tbody/tr[1]/td[1]/strong').text.split(' ')[1])
		ally.hp = int(locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/table/tbody/tr[2]/td[2]/strong').text.split(' ')[1])
#		print('After: Enemy hp:', enemy.hp, 'Ally hp:', ally.hp)

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
		if best_pokemon == None:
			battle.current_ally = None
		else:
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
					break
			if strongest_move.damage >= enemy.hp:
				break
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
		self.current_enemy = 0

	def init_hp(self):
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

	def continue_button(self):
		self.fighttype.continue_button()
	def select_ally(self):
		self.fighttype.select_ally(self.current_ally.slot)
	def last_enemy(self):
		return True if self.current_enemy + 1 == len(self.enemies) else False

	def throw(self, pokeballs, ball):
		options = { 'Poké Ball' : 'Pokéball', 'Great Ball' : 'Great Ball', 'Ultra Ball' : 'Ultra Ball', 'Beast Ball' : 'Beast Ball' }
		locateElement(driver, By.XPATH, '//label[contains(., "' + options[ball] + '")]').click()
		pokeballs[ball] -= 1
		locateElement(driver, By.XPATH, '//*[@id="itemForm"]/table/tbody/tr[20]/td/input[3]').submit()
		finish_loading()
		self.fighttype.update_hp(self.enemies[self.current_enemy], self.current_ally)

	def catch(self, pokeballs):
		enemy = self.enemies[self.current_enemy]
		for _ in range(len([x for x in self.allies if not x.dead()])):
			while not self.current_ally.dead():
				pokeball = None
				if enemy.level >= 75:
					pokeball = 'Beast Ball'
				elif enemy.hp <= 10 and pokeballs['Poké Ball'] != 0:
					pokeball = 'Poké Ball'
				elif enemy.hp <= 20 and pokeballs['Great Ball'] != 0:
					pokeball = 'Great Ball'
				elif pokeballs['Ultra Ball'] != 0:
					pokeball = 'Ultra Ball'
				else:
					print ("No remaining poke balls!")
					return False
				self.throw(pokeballs, pokeball)
				if "The wild Pokémon has been caught." in locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/div/strong[2]').text:
					locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input').click()
					finish_loading()
					return True
				locateElement(driver, By.XPATH, '//*[@id="battleForm"]/div/input').click()
				finish_loading()
			remaining_allies = [x for x in self.allies if not x.dead()]
			if not remaining_allies:
				return False
			self.current_ally = remaining_allies[0]
			self.select_ally()
		return False

	#Completes a 'fight', fight is classified as 6 allies and 1-6 enemies
	#If the hp of the last enemy has reached the target (defined by the FightType) the function will return True
	#If all allies have died and the enemy hasn't reached it's target, the function will return False
	def fight(self, minimum_duration=0):
		if not self.allies:
			self.init_hp()
		global last_battle_won
		while self.current_enemy < len(self.enemies):
			enemy = self.enemies[self.current_enemy]
			remaining_allies = len([x for x in self.allies if not x.dead()])
			if remaining_allies == 0:
				return False
			for _ in range(remaining_allies): #loop over all living allies
				moveset = self.fighttype.get_moveset(self,enemy)
#				print(moveset)
				if not self.current_ally:
					print("No valid option could be found")
					return False
#				print("Current ally:", self.current_ally.name, "slot:", self.current_ally.slot)
#				print(moveset)
				self.select_ally()
				for move in moveset:
					while True:
						if self.attack(move) == True or self.current_ally.dead():
#							print("attack hit")
							break
#						print("attack missed")
					if self.current_ally.dead() or enemy.hp_in_range(self.target_range):
#						finish_loading()
						if enemy.hp_in_range(self.target_range) and self.last_enemy():
							while time.time() <= last_battle_won + minimum_duration:
								time.sleep(0.5)
							self.continue_button()
							finish_loading()
							last_battle_won = time.time()
							return True
						self.continue_button()
						finish_loading()
						break
					if self.target_range[0] == 1:
						self.continue_button() #breaks on sidequest
						finish_loading() #same
				if enemy.hp_in_range(self.target_range):
					self.current_enemy += 1
					break
		return False

	#bug: if enemy is burned/taking DOT, this will return True, causing the battle to time out
	#ditto is still going to break my new system for the first move
	def attack(self, move):
		enemy = self.enemies[self.current_enemy]
		hp_before = enemy.hp
#		print("Damage done by", move, '=', self.current_ally.moves[move].damage)
		self.fighttype.attack(move)
		self.fighttype.update_hp(enemy, self.current_ally)
#		print("Damage of current move:", self.current_ally.moves[move].damage)
#		print("HP before:", hp_before, "HP after:", enemy.hp, "difference:", hp_before - enemy.hp)
		if hp_before == enemy.hp:
			if self.target_range[0] == 1:
				self.continue_button()
			return False
		return True if (enemy.dead() or hp_before - enemy.hp >= self.current_ally.moves[move].damage) else False

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
		self.damage = int((self.basedmg * self.get_multiplier(enemy.types) * (0.75 if enemy.special == "Metallic" else 1) / 60) + 0.5)

#---------------------------------------MAIN----------------------------------------

player = Player()
player.login()
player.init_team()
player.init_inv()
player.restock()

if config['mode'] == "catch":
	while True:
		if any (player.items[ball] == None or player.items[ball] < config['restock'][ball]['min'] for ball in ['Poké Ball', 'Great Ball', 'Ultra Ball']):
			player.restock()
		player.gotta_catch_em_all()
		player.catch()
elif config['mode'] == "sidequest":
	player.sidequest_loop()
elif config['mode'] == "gyms":
	player.gyms()
#else if config['mode'] == "clanbattle"
#	player.clanbattle_loop
