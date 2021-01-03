# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    poke_entry.py                                      :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2021/01/01 19:53:10 by tbruinem      #+#    #+#                  #
#    Updated: 2021/01/01 20:52:03 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

class PokeEntry:
	def __init__(self, name="", types=[], moves=[]):
		self.name = name
		self.types = types
		self.moves = moves