# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    vortex_attackdex.py                                :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2020/12/31 15:49:16 by tbruinem      #+#    #+#                  #
#    Updated: 2020/12/31 16:01:45 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from selenium.webdriver.common.by import By
from datetime import datetime

from threading import Thread, Lock
import json, time, random, sys, os
import pokebase as pb
import re

PATH = "./req/chromedriver.exe"
driver = webdriver.Chrome(PATH)

driver.get("https://wiki.pokemon-vortex.com/wiki/Attackdex")

moves = driver.find_elements(by=By.XPATH, value="//*[@id=\"mw-content-text\"]/div/table/tbody/*")

for move in moves:
	movetype = move.get_attribute("class").split('-')[1]
	children = move.find_elements(by=By.XPATH, value="./*")
	print (movetype, "=", children[0].text.replace(' ','-').lower(), children[3].text)
