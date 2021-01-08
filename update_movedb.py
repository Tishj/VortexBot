# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    update_movedb.py                                   :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2021/01/02 10:56:07 by tbruinem      #+#    #+#                  #
#    Updated: 2021/01/08 00:07:04 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

import pickle
import requests
from lxml import html

movedb = dict()
content = html.fromstring(requests.get('https://wiki.pokemon-vortex.com/wiki/Attackdex').content)
moves = content.xpath('//*[@id=\"mw-content-text\"]/div/table/tbody/*')

for move in moves:
	name, movetype, cost, power, acc, category = move.xpath('./*')
#	print(name.text, movetype.attrib['class'], cost.text, power.text, acc.text, category.text)
	movename = name.text
	if not movename:
		continue
	print(movename[:-1])
	movedb[movename[:-1]] = (movetype.attrib['class'], int(power.text))

movedb['Poison Powder'] = ('grass', 0)

with open('movedb', 'wb') as f:
	pickle.dump(movedb, f, pickle.HIGHEST_PROTOCOL)

print("PokemonVortex movedatabase succesfully updated!, saved under 'movedb'")