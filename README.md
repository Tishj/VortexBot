
#  VortexBot v5

Bot for pokemon-vortex.com v5, running in Python with Selenium in Chrome (on Windows)

### - Setup

To install all the dependencies, run: 
`sudo python3 setup.py install` 

It is recommended to update the move, multiplier and pokemon database files (pickled Dictionaries)
To do so run:
`python3 update_movedb.py`
`python3 update_multiplierdb.py`
`python3 update_pokedb.py`

###  - Selenium

For Selenium we're going to need to install the ChromeDriver (WebDriver for Chrome), from:

http://chromedriver.chromium.org/downloads

The ChromeDriver version should match your current Chrome version, to see what that is, go to:

`chrome://settings/help`

Place the downloaded `chromedriver.exe` in the `req` folder of this repository

### - Usage

Once you've finished setting up the `config.yml` you can run the bot with `python3 vortexbot.py`

###  - Config

The config is where the bot gets all it's inputs from, you need to set this up locally (config.yml)

It's a YML file that you will need to set up before using, the fields that are required to change are 'username' and 'password'.
- ##### Player
```
player:
  username: 'my_username'
  password: '12345abcd'
```
- ##### Desired Pokemon
	This is a list containing all the names/types the catcher should respond to, examples include:
	- `Shiny Charmander`
	- `Shadow`
	- `Lugia`

- ##### Modes
  - `catch` - Walk from left to right until pokemon from `desired_pokemon` show up
  - `sidequest` - Battle all sidequests, leaving 10 seconds between each victory at the minimum, collecting rewards inbetween and resetting sidequests once all have been finished. (2121 at the time of writing) (RISKY)
  - `gyms` - Battle all required gyms needed to catch legendaries (excludes the final battles)
  - `clanbattle` - Similar to sidequest, fight clanbattles until stopped

### Warranty
I take no responsibility if your account got banned because you used this tool
