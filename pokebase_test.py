# **************************************************************************** #
#                                                                              #
#                                                         ::::::::             #
#    pokebase_test.py                                   :+:    :+:             #
#                                                      +:+                     #
#    By: tbruinem <tbruinem@student.codam.nl>         +#+                      #
#                                                    +#+                       #
#    Created: 2020/12/29 12:00:45 by tbruinem      #+#    #+#                  #
#    Updated: 2020/12/29 14:31:15 by tbruinem      ########   odam.nl          #
#                                                                              #
# **************************************************************************** #

import pokebase as pb

move = pb.move('bite').type
types = pb.pokemon('nidoran-m').types
print(move)
for poketype in types:
	print(poketype.type)