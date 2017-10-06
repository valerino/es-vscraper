what it is
----------
es-vscraper is an extensible scraper to generate gamelist.xml and manage games collections, compatible with [EmulationStation/RetroPie](https://retropie.org.uk/),  [RecalBox/RecalBoxOS](https://www.recalbox.com/) and any other project sharing the [EmulationStation Gamelist XML format](https://github.com/Aloshi/EmulationStation/blob/master/GAMELISTS.md).

This is a personal project made just for myself (at the moment), since i don't like the available hash-only-based scrapers.

dependencies
------------
(tested on Linux, retropie/raspi, OSX)
~~~~
sudo apt-get update (needed on retropie/raspi, seems....)
sudo apt-get install python3 python3-pip libxml2-dev libxslt-dev
sudo pip3 install requests Image bs4 lxml python-slugify fuzzywuzzy python-Levenshtein
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
es-vscraper needs correctly named game files (i.e. 'bubble bobble.bin'), i don't like hash-based systems since a variation in the hash leads to no hits most of the times (unless you download specific rom-sets, which is not an option for me, too much wasted time!).
either, you may use the 'to_search' option to search for a specific name, associating it to the file you provide via 'path' (only for single query mode)

~~~~
-------
WARNING
-------
be careful to use multi-query mode (when 'path' refers to an entire folder):
it may take long and/or cause your ip to be banned for hammering
(even though i added random sleep() of few seconds between queries)!
~~~~

installation
------------
(example on retropie/raspi)
~~~~
sudo su -
cd /opt
git clone https://github.com/valerino/es-vscraper
~~~~

usage
-----
~~~~
pi@retropie:/opt/es-vscraper $ ./es-vscraper.py --help
usage: Manage games collection and build gamelist.xml by querying online databases

       [-h] [--list_engines] [--engine [ENGINE]]
       [--engine_params [ENGINE_PARAMS]] [--download_url [DOWNLOAD_URL]]
       [--download_no_overwrite] [--name_from_url] [--path [PATH]]
       [--to_search [NAME]] [--delete_no_scraped] [--sleep [SECONDS]]
       [--trunc_at [CHARACTERS]] [--gamelist_path [GAMELIST_PATH]]
       [--overwrite] [--img_path [IMG_PATH]] [--img_index [IMG_INDEX]]
       [--img_thumbnail] [--append [STRING]] [--append_auto N]
       [--unattended_timeout [SECONDS]] [--dumpbin [PATH]] [--purge [REGEX]]
       [--preprocess [REGEX]] [--preprocess_duplicates] [--preprocess_test]
       [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --list_engines        list the available engines (and their options, if any)
  --engine [ENGINE]     the engine to use (use '--list_engines' to check
                        available engines)
  --engine_params [ENGINE_PARAMS]
                        custom engine parameters, name=value[,name=value,...],
                        default None
  --download_url [DOWNLOAD_URL]
                        url to download the file at '--path', which will be
                        overwritten if existent
  --download_no_overwrite
                        if specified, '--download_url' do not overwrites
  --name_from_url       if specified, '--path' must point to a destination
                        folder and the filename is derived from '--
                        download_url'
  --path [PATH]         path to the file to be scraped (needs to specify '--
                        to_search'), or to a folder with (correctly named)
                        files to be scraped
  --to_search [NAME]    name of the game to search for enclosed in '' if
                        containing spaces, the more accurate the better.
                        Default is the filename at '--path' or the one derived
                        from '--url', stripped of extension. Ignored if '--
                        path' refers to a folder
  --delete_no_scraped   delete non-scraped files, ignored if '--dumpbin' is
                        specified. Ignored if '--path' refers to a file
  --sleep [SECONDS]     sleep random seconds (1..SECONDS) between each scraped
                        entries when path refers to a folder. Default is 15.
                        Ignored if '--path' refers to a file
  --trunc_at [CHARACTERS]
                        before using '--path' as search key, truncate at the
                        first occurrence of any of the given characters (i.e.
                        --path './caesar the cat, (demo) (eng).zip' --trunc_at
                        '(,' searches for 'caesar the cat')
  --gamelist_path [GAMELIST_PATH]
                        path to gamelist.xml (default '<path>/gamelist.xml',
                        will be created if not found or appended to)
  --overwrite           existing entries in gamelist.xml will be overwritten.
                        Default is to skip existing entries
  --img_path [IMG_PATH]
                        path to the folder where to store images (default
                        '<path>/images)'
  --img_index [IMG_INDEX]
                        download image at 0-based index among available images
                        (default 0=first found, -1 tries to download boxart if
                        found or fallbacks to first image found)
  --img_thumbnail       download image thumbnail (support depends on the
                        scraper engine)
  --append [STRING]     append this string (enclosed in '' if containing
                        spaces) to the game name in the gamelist.xml file.
                        Only valid if '--path' do not refer to a folder
  --append_auto N       automatically generate n entries starting from the
                        given one (i.e. --append_auto 2 --path=./game1.d64
                        generates 'game (disk 1)' pointing to ./game1.d64 and
                        'game (disk 2)' pointing to ./game2.d64). Only valid
                        if '--path' do not refer to a folder
  --unattended_timeout [SECONDS]
                        automatically choose the first found entry after the
                        specified seconds, in case of multiple entries found
                        (default is to ask on multiple choices)
  --dumpbin [PATH]      move non-scraped, not matching from '--preprocess' or
                        duplicates from '--preprocess_duplicates' files to
                        this path if specified
  --purge [REGEX]       delete all the entries whose path matches the given
                        regex from the gamelist.xml (needs '--gamelist_path',
                        anything else is ignored). This also deletes the
                        affected game files!
  --preprocess [REGEX]  preprocess folder at '--path' and keep only the files
                        matching the given regex (every other parameter is
                        ignored). This cleans the directory for later
                        processing by the scraper
  --preprocess_duplicates
                        check for duplicates (and ask for deletion or moving
                        to '--dumpbin' if specified)
  --preprocess_test     test for preprocessing options, do not delete/move
                        files
  --debug               Print scraping result on the console
~~~~

sample usage
------------
~~~~
/opt/es-vscraper/es-vscraper.py --engine lemon-c64 --to_search "caesar the cat" --path "/home/pi/RetroPie/roms/c64/caesar.prg"

/opt/es-vscraper/es-vscraper.py --engine lemon-c64 --path "/home/pi/RetroPie/roms/c64/caesar\ the\ cat.prg"

/opt/es-vscraper/es-vscraper.py --engine lemon-c64 --path /home/pi/RetroPie/roms/c64
~~~~

advanced usage
--------------
keep only PAL roms in atari 2600 folder (move non PAL to ./moved folder):
~~~~
/opt/es-vscraper/es-vscraper.py --path ./atari2600 --preprocess '.+(PAL).+' --dumpbin ./moved
~~~~
...removing duplicates (interactive, will ask for confirmations), duplicates will be moved to ./moved folder
~~~~
/opt/es-vscraper/es-vscraper --preprocess_duplicates --dumpbin ./moved --path ./atari2600
~~~~
...then scrape the whole folder, trying to get the right name from filename, in fully automated mode (no ask for confirmation), saving the non-scraped roms for later inspection
~~~~
/opt/es-vscraper/es-vscraper.py --engine atariage-atari --engine_params system=2600 --trunc_at '([' --path /home/pi/RetroPie/roms/atari2600 --dumpbin ./not-scraped --unattended_timeout 1 --sleep 3
~~~~


currently implemented modules
-----------------------------
- Commodore Amiga
	- Lemon (http://www.lemonamiga.com)

- Commodore 64
	- Lemon (http://www.lemon64.com)

- Sinclair (ZX Spectrum, ZX81)
	- World of Spectrum (http://www.worldofspectrum.org)

- Multi
	- Games Database (http://www.gamesdatabase.org)
		- supported systems: http://www.gamesdatabase.org/systems

- Multi (Atari)
	- AtariAge (http://atariage.com)
		- supported systems: 2600, 5200, 7800, lynx, jaguar

todo
----
- Implement more scrapers :)

