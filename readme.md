what it is
----------
es-vscraper is an extensible scraper for [EmulationStation](https://github.com/Aloshi/EmulationStation).

This is a personal project made just for myself (at the moment), since i don't like the available hash-only-based scrapers.

dependencies
------------
~~~~
sudo apt-get install python3 python3-pip3
sudo pip3 install requests Image bs4 lxml
~~~~

on osx/windows, install python3 separately then install the dependencies with pip3 as normal

how to write a plugin
---------------------
. create subdirectory in 'scrapers', named 'name-system' (i.e. 'lemon-amiga')

. implement 'name-system.py' module (i.e. 'scrapers/lemon-amiga.py')

. each plugin must implement the following functions:
~~~~
def run_direct_url(u, img_index=0, img_cover=False):
  """
  perform query with the given direct url
  :param u: the game url
  :param img_index: 0-based index of the image to download, default 0
  :param img_cover: True to download boxart cover as image, default False. If boxart is not available, the first image found is used
  :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each may be empty)
  """

def run(to_search, img_index=0, img_cover=False):
  """
  perform query with the given game title
  :param to_search: the game title
  :param img_index: 0-based index of the image to download, default 0
  :param img_cover: True to download boxart cover as image, default False. If boxart is not available, the first image found is used
  :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each may be empty)
  """

def name():
  """
  the plugin name
  :return: string (i.e. 'lemon64')
  """

def url():
  """
  the plugin url name
  :return: string (i.e. 'http://www.lemon64.com')
  """

def system():
  """
  the related system (descriptive)
  :return: string (i.e. 'Commodore 64')
  """

def system_short():
  """
  the related system (short)
  :return: string (i.e. 'c64')
  """
~~~~

. internal implementation is up to the plugin

notes
----
At the moment it is meant to be used for creating/updating existing gamelist.xml by searching for single games (need to check with each database provider for permission to implement directory-tree scanning, might be too heavy for their traffic).

es-vscraper needs correctly named game files (i.e. 'bubble bobble.bin'), i don't like hash-based systems since a variation in the hash leads to no hits most of the times (unless you download specific rom-sets, which is not an
option for me, too much wasted time!).

usage
-----
~~~~
usage: Build gamelist.xml for EmulationStation by querying online databases

       [-h] [--list_engines] [--engine [ENGINE]] [--to_search [TO_SEARCH]]
       [--path [PATH]] [--gamelist_path [GAMELIST_PATH]]
       [--img_path [IMG_PATH]] [--img_index [IMG_INDEX]] [--img_cover]
       [--unattended] [--debug]


       optional arguments:
         -h, --help            show this help message and exit
         --list_engines        list the available engines
         --engine [ENGINE]     the engine to use (use --list_engines to check
                               available engines)
         --to_search [TO_SEARCH]
                               the game to search for (full or sub-string), case
                               insensitive, enclosed in " " (i.e. "game")
         --path [PATH]         path to the single game file or path to games folder
         --gamelist_path [GAMELIST_PATH]
                               path to gamelist.xml (default "./gamelist.xml", will
                               be created if not found or appended to)
         --img_path [IMG_PATH]
                               path to the folder where to store images (default
                               "./images")
         --img_index [IMG_INDEX]
                               download image at 0-based index among available images
                               (default 0, first found)
         --img_cover           try to download boxart cover if available, either it
                               will download the first image found
         --unattended          Automatically choose the first found entry in case of
                               multiple entries found (default False, asks on
                               multiple choices)
         --debug               Print scraping result on the console

~~~~

sample usage
------------
./es-vscraper.py --engine lemon-c64 --to_search "caesar the cat" --path ./caesar\ the\ cat.prg

currently implemented modules
-----------------------------
. Commodore Amiga
- Lemon (http://www.lemonamiga.com)

. Commodore 64
- Lemon (http://www.lemon64.com)

todo
----
. Tested on Linux and OSX, but should work on any OS with python3 (including raspberry, of course)

. At the moment, only works for single game ('path' must be a game file)

. Implement more systems :)
