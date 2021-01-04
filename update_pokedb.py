# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    update_pokedb.py                                   :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2021/01/01 19:56:25 by tbruinem      #+#    #+#                  #
#    Updated: 2021/01/04 19:12:59 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

import pickle
import requests
from lxml import html
from poke_entry import PokeEntry
import re

pokedb = dict()
pokedex = requests.get('https://wiki.pokemon-vortex.com/wiki/Pokedex')

WIKI_URL = "https://wiki.pokemon-vortex.com/"

website = html.fromstring(pokedex.content)
pokemon_names = website.xpath('//td[contains(@class, "dex")]/a[2]')
for name in pokemon_names:
	pokename = name.text
	if pokename == None:
		continue
	types = []
	moves = []
	entry = html.fromstring(requests.get(WIKI_URL + name.get("href")).content)
	raw = entry.xpath('//*[@id="mw-content-text"]/div/table[2]/tbody/tr[3]/td/a[*]')
	for poketype in raw:
		typename = poketype.get("title")
		types.append(typename)
#		print(typename)
# 	raw = entry.xpath('//*[@id="Attacks"]/./../../*/*/*[@class="container-attacks"]/./../tr[*]/td[1]')
# 	print(raw)
# #	raw = entry.xpath('//*[@id="mw-content-text"]/div/table[6]/tbody/tr[*]/td[1]')
# 	print("-- Moves:")
# 	for move in raw:
# 		print(move.tag)
# 		text = move.text
# 		if text == None:
# 			continue
# 		movename = text[:-1].lower().replace(' ', '-')
# 		moves.append(movename)
# 		print(movename)
#	print('----------------')
	pokedb[pokename] = PokeEntry(name=pokename, types=types, moves=moves)
	print(pokename)

#wiki editors are retarded
pokedb["Farfetch'd"] = pokedb.pop('Farfetchd')
pokedb["Farfetch'd (Galarian)"] = pokedb.pop('Farfetchd (Galarian)')

with open('pokedb', "wb") as f:
	pickle.dump(pokedb, f, pickle.HIGHEST_PROTOCOL)

print("Pokedb succesfully updated! Stored under the name 'pokedb'")