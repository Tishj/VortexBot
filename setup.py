#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
	name="vortex-bot-v5",
	version="0.0.0.1",
	description="Python-Selenium bot for pokemon-vortex.com",
	long_description="Automates tasks in the game pokemon-vortex at pokemon-vortex.com, using Selenium primarily",
	url="https://github.com/tishj/VortexBot",
	author="Tishj",
	license='MIT',
	packages = find_packages(),
	install_requires = ['selenium==4.0.0.a7', 'requests', 'datetime', 'lxml', 'pyyaml', 'trio' ],
)
