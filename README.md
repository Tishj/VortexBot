
#  VortexBot v5

Bot for pokemon-vortex.com v5, running in Python with Selenium in Chrome (on Windows and Mac)

### - Setup

To install all the dependencies, run: 
`sudo python3 setup.py install` 

It is recommended to update the move, multiplier and pokemon database files, but might not be required
To do so run:
`python3 update_movedb.py`
`python3 update_multiplierdb.py`
`python3 update_pokedb.py`

###  - Selenium

For Selenium we're going to need to install the ChromeDriver (WebDriver for Chrome), from:

http://chromedriver.chromium.org/downloads

The ChromeDriver version should match your current Chrome version, to see what that is, go to:

`chrome://settings/help`

Place the downloaded `chromedriver.exe` (or `chromedriver` on Mac) in the `req` folder of this repository

### - Usage

Once you've finished setting up the `config.yml` you can run the bot with `python3 vortexbot.py`

###  - Config

The `config.yml` is where the bot gets all it's inputs from

It's a YML file that you will need to set up before starting the bot, the fields that are required to change are 'username' and 'password'.
- ##### Player
    ```
    player:
    username: 'my_username'
    password: '12345abcd'
    ```
- ##### Pokemon
    For every rarity type, namely `COMMON`, `RARE`, `LEGENDARY`, `ULTRA` you can set up groups to select pokemon on, or leave them empty to catch every pokemon of that rarity
    For example below config will only catch COMMON pokemon if they meet the property requirement(s) of one of the following  groups:
     - `not in collection` which is `caught: 0` (not obtained)
     - `shiniesss` which is `special: Shiny`
     - `unhealthy obsession` which is `special: Metallic` AND `name: Klink`
 
    And will always catch other rarity types because they have no group(s)
    ```
    pokemon:
      COMMON:
        not in collection:
          caught:
            - 0
        shiniesss:
          special:
            - Shiny
        unhealthy obsession:
          special:
            - Metallic
          name:
            - Klink
      RARE:
      LEGENDARY:
      ULTRA:
    ```
    The list of properties that can be used in the groups is:
    - ##### Properties:
     `caught` 
     
		'0' - (not obtained)
        '1' - (obtained, but not this season)
        '2' - (obtained, this season)
     `name` 
     
		'Swablu' - (any pokemon name from that rarity)
     `special` 
     
		'Shiny'
		'Shadow'
		'Dark'
		'Mystic'
		'Metallic'

- ##### Restock
  For every regular pokeball (Poke Ball, Great Ball and Ultra Ball) specify at what point the bot should restock them (`min`) and up to what amount it should buy them (`goal`)

- ##### Modes
  - `catch` - Walk from left to right until a pokemon matching the config shows up, it will catch it and repeat.
  - `sidequest` - Battle all sidequests, leaving 10 seconds between each victory at the minimum, collecting rewards inbetween and resetting sidequests once all have been finished. (2121 at the time of writing) (RISKY)
  - `gyms` - Battle all required (remaining) gyms needed to catch legendaries (excludes the final battles).
  - `clanbattle` - Similar to sidequest, fight clanbattles until stopped.
  - `wildfight` - Instead of catching wild pokemon, you can defeat any pokemon from your selection groups.
  - `anything else` Use this option to fight a trainer or gym on repeat, for example: `battle-gym/Brock`

### Disclaimer
I take no responsibility if your account got banned because you used this tool
