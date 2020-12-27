from selenium import webdriver
from selenium.webdriver.common.keys import Keys

PATH = "./req/chromedriver.exe"

driver = webdriver.Chrome(PATH)

driver.get("https://www.unovarpg.com/signin/")
username_field = driver.find_element_by_name("username")
password_field = driver.find_element_by_name("password")
login_button = driver.find_element_by_id("buttonLogin")

username_field.send_keys("pokefan5005")
password_field.send_keys("testtest")
login_button.send_keys(Keys.RETURN)

print("*Hacker voice* : \"I'M IN\"")

driver.get("https://www.unovarpg.com/map.php?map=1&zone=1")

try:
	driver.find_element_by_class_name("form-button-default small lblue")
	pokemon_box = driver.find_element_by_class_name("event-screen")
	print(pokemon_box)
except:
	print("No pokemon was found")

