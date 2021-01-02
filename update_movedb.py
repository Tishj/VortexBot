# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    update_movedb.py                                   :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2020/12/31 16:16:22 by tbruinem      #+#    #+#                  #
#    Updated: 2020/12/31 16:23:19 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

from selenium import webdriver
from selenium.webdriver.common.by import By
import pickle

movedb = dict()

PATH = "./req/chromedriver.exe"
driver = webdriver.Chrome(PATH)

driver.get("https://wiki.pokemon-vortex.com/wiki/Attackdex")

moves = driver.find_elements(by=By.XPATH, value="//*[@id=\"mw-content-text\"]/div/table/tbody/*")

for move in moves:
	movetype = move.get_attribute("class").split('-')[1]
	information = move.find_elements(by=By.XPATH, value="./*")
	movedb[information[0].text.replace(' ','-').lower()] = (movetype, int(information[3].text))

with open("movedb", "wb") as f:
	pickle.dump(movedb, f, pickle.HIGHEST_PROTOCOL)

driver.quit()
print("PokemonVortex movedatabase succesfully updated!, saved under 'movedb'")