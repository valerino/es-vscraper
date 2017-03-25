what it is
----------
es-vscraper is an extensible scraper to generate gamelist.xml compatible with [EmulationStation/RetroPie](https://retropie.org.uk/),  [RecalBox/RecalBoxOS](https://www.recalbox.com/), and any other project sharing the [EmulationStation Gamelist XML format](https://github.com/Aloshi/EmulationStation/blob/master/GAMELISTS.md).

This is a personal project made just for myself (at the moment), since i don't like the available hash-only-based scrapers.

dependencies
------------
(tested on Linux, retropie/raspi, OSX)
~~~~
sudo apt-get update (needed on retropie/raspi, seems....)
sudo apt-get install python3 python3-pip libxml2-dev libxslt-dev
sudo pip3 install requests Image bs4 lxml python-slugify
(lxml takes some minutes to build on raspi)
~~~~
on OSX, install python3 and any other needed library with brew (preferred)

on Windows, install python3 and the other libraries separately (untested)

In the end, install the python stuff with pip3

how to write a scraper engine
---------------------
- create subdirectory in 'scrapers', named 'name-system' (i.e. 'lemon-amiga')

- implement 'name-system.py' module (i.e. 'scrapers/lemon-amiga.py')

- each plugin must implement the following functions:
~~~~
def run_direct_url(u, args):
  """
  perform query with the given direct url
  :param u: the game url
  :param args: arguments from cmdline
  :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each except 'name' may be empty)
  """

def run(args):
  """
  perform query with the given game title
  :param args: arguments from cmdline
  :throws vscraper_utils.GameNotFoundException when a game is not found
  :throws vscraper_utils.MultipleChoicesException when multiple choices are found. ex.choices() returns [{ name, publisher, year, url, system}] (each except 'name' may be empty)
  :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each except 'name' may be empty)
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

def systems():
  """
  the related system/s (descriptive)
  :return: string (i.e. 'Commodore 64')
  """

def engine_help():
  """
  help on engine specific '--engine_params' and such
  :return: string
  """
~~~~

. internal implementation is up to the plugin

notes
----
At the moment es-vscraper is meant to be used for creating/updating existing gamelist.xml by searching for single games (need to check with each database provider for permission to implement directory-tree scanning, might be too heavy for their traffic).

es-vscraper needs correctly named game files (i.e. 'bubble bobble.bin'), i don't like hash-based systems since a variation in the hash leads to no hits most of the times (unless you download specific rom-sets, which is not an
option for me, too much wasted time!).

installation
------------
(example on retropie/raspi)
~~~~
sudo su -
cd /opt
git clone https://github.com/valerino/es-vscraper
exit
~~~~

usage
-----
~~~~
usage: Build gamelist.xml for EmulationStation by querying online databases

       [-h] [--list_engines] [--engine [ENGINE]]
       [--engine_params [ENGINE_PARAMS]] [--path [PATH]]
       [--to_search [TO_SEARCH]] [--gamelist_path [GAMELIST_PATH]]
       [--img_path [IMG_PATH]] [--img_index [IMG_INDEX]] [--img_thumbnail]
       [--append [APPEND]] [--append_auto APPEND_AUTO] [--unattended]
       [--delete [DELETE]] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --list_engines        list the available engines (and their options, if any)
  --engine [ENGINE]     the engine to use (use --list_engines to check
                        available engines)
  --engine_params [ENGINE_PARAMS]
                        custom engine parameters, name=value[,name=value,...],
                        default None
  --path [PATH]         path to the file to be scraped
  --to_search [TO_SEARCH]
                        the game to search for (full or sub-string), case
                        insensitive, enclosed in "" if containing spaces.
                        Default is the filename part of path without extension
  --gamelist_path [GAMELIST_PATH]
                        path to gamelist.xml (default path/gamelist.xml, will
                        be created if not found or appended to)
  --img_path [IMG_PATH]
                        path to the folder where to store images (default
                        path/images)
  --img_index [IMG_INDEX]
                        download image at 0-based index among available images
                        (default 0=first found, -1 tries to download boxart if
                        found or fallbacks to first image found)
  --img_thumbnail       download image thumbnail, if possible
  --append [APPEND]     append this string (enclosed in "" if containing
                        spaces) to the game name in the gamelist.xml file
  --append_auto APPEND_AUTO
                        automatically generate n entries starting from the
                        given one (i.e. --append_auto 2 --path=./game1.d64
                        generates "game (disk 1)" pointing to ./game1.d64 and
                        "game (disk 2)" pointing to ./game2.d64)
  --unattended          Automatically choose the first found entry in case of
                        multiple entries found (default False, asks on
                        multiple choices)
  --delete [DELETE]     delete all the entries whose path matches this regex
                        from the gamelist.xml (needs --gamelist_path)
  --debug               Print scraping result on the console
~~~~

sample usage
------------
/opt/es-vscraper/es-vscraper.py --engine lemon-c64 --to_search "caesar the cat" --path ./caesar\ the\ cat.prg
/opt/es-vscraper/es-vscraper.py --engine lemon-c64 --path "./caesar\ the\ cat.prg"

currently implemented modules
-----------------------------
- Commodore Amiga
  - Lemon (http://www.lemonamiga.com)

- Commodore 64
  - Lemon (http://www.lemon64.com)

- Multi
  - Games Database (http://www.gamesdatabase.org)
    - supported systems: http://www.gamesdatabase.org/systems

todo
----
- Tested on Linux, OSX, retropie/raspi

- At the moment, only works for single game ('path' must be a game file)

- Implement more scrapers :)
