# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    newapproach.py                                     :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2020/12/28 15:20:52 by tbruinem      #+#    #+#                  #
#    Updated: 2020/12/28 15:27:26 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

from selenium import webdriver
import logging
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.bidi import cdp
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from datetime import datetime

#---------------------------------------SETUP--------------------------------------------

# load the desired webpage

PATH = "./req/chromedriver.exe"
WINDOW_SIZE = "1920,1080"

WINDOW_SIZE = "1920,1080"

driver = webdriver.Chrome(PATH)

driver.get("https://www.pokemon-vortex.com/login/")

login_button = driver.find_element_by_id("submit")

text = login_button.get_attribute("value")
print(text)

driver.execute_script('document.querySelector("#submit").value = "yeet"')
text = login_button.get_attribute("value")
print(text)

#driver.quit()
quit()