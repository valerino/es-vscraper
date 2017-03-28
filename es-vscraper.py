#!/usr/bin/env python3
"""
es-vscraper

MIT-LICENSE

Copyright 2017, Valerio 'valerino' Lupi <xoanino@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import argparse
import importlib
import os
import re
import traceback

import sys

import vscraper_utils
from lxml import etree, objectify

SCRAPERS_FOLDER = 'scrapers'

def list_scrapers():
    """
    get scrapers in ./scrapers folder
    :return: [ modules]
    """
    cwd = os.getcwd()
    os.chdir(sys.path[0])
    scrapers = []
    files = os.listdir('./%s' % SCRAPERS_FOLDER)
    for f in files:
        path = os.path.join('./scrapers', f)
        if not os.path.isdir(path) or not ('%s.py' % f) in os.listdir(path):
            continue
        try:
            scraper = '%s.%s.%s' % (SCRAPERS_FOLDER, f, f)
            mod = importlib.import_module(scraper)
            scrapers.append(mod)
        except:
            continue
    
    os.chdir(cwd)
    return scrapers


def get_scraper(engine):
    """
    get the desired scraper
    :param engine: scraper name
    :return: module
    """
    cwd=os.getcwd()
    os.chdir(sys.path[0])
    path = os.path.join('./scrapers', engine)
    if not os.path.exists(path) or not os.path.exists(os.path.join(path, '%s.py' % engine)):
        os.chdir(cwd)
        raise FileNotFoundError('Scraper "%s" is not installed!' % engine)

    try:
        scraper = '%s.%s.%s' % (SCRAPERS_FOLDER, engine, engine)
        os.chdir(cwd)
        return importlib.import_module(scraper)
    except Exception as e:
        os.chdir(cwd)
        raise ImportError('Cannot import scraper "%s"' % engine)


def add_game_entry(args, root, game_info):
    """
    adds/replace an entry to the gamelist xml
    :param args: dictionary
    :param root: 'gameList' root entry
    :param game_info: a dictionary
    :return:
    """

    # check if game is already there
    game = None
    for g in root.findall('game'):
        if g.path == game_info['path']:
            # found, use this and replace content
            game = g
            print('Replacing entry: %s' % game_info['name'])
            break

    if game is None:
        # create new entry
        print ('Creating entry: %s' % game_info['name'])
        game = objectify.Element('game')

    # fill values
    game.name = game_info['name']
    game.developer = game_info['developer']
    game.publisher = game_info['publisher']
    game.desc = game_info['desc']
    game.genre = game_info['genre']
    game.releasedate = game_info['releasedate']
    if args.relative_paths:
        # games and images are relative paths
        if game_info['image'] is not None:
            game.image = os.path.join('./images', os.path.basename(game_info['image']));
        game.path = os.path.join('./', os.path.basename(game_info['path']));
    else:
        game.path = game_info['path'] 
        if game_info['image'] is not None:
            game.image = game_info['image']

    # append entry
    root.append(game)


def scrape_title(engine, args):
    """
    scrape a single title
    :param engine an engine module
    :param args dictionary
    :return:
    """
    if not os.path.exists(args.path):
        print('%s not found!' % args.path)
        return

    if args.to_search is None:
        # to_search (name to be queried by scraper) is the filename without extension
        args.to_search = os.path.splitext(os.path.basename(args.path))[0]
    if args.img_path is None:
        # use path/images as images path
        args.img_path=os.path.join(os.path.dirname(args.path), 'images')
    if args.gamelist_path is None:
        # use path/gamelist.xml as gamelist path
        args.gamelist_path=os.path.join(os.path.dirname(args.path), 'gamelist.xml')

    try:
        print('Downloading data for "%s" (%s)...' % (args.to_search, '-' if args.engine_params is None else args.engine_params))
        game_info = engine.run(args)
    except vscraper_utils.GameNotFoundException as e:
        print('Cannot find "%s", scraper="%s"' % (args.to_search, engine.name()))
        return
    except vscraper_utils.MultipleChoicesException as e:
        print('Multiple titles found for "%s":' % args.to_search)
        i = 1
        for choice in e.choices():
            print('%s: [%s] %s, %s, %s' % (i, choice['system'] if 'system' in choice else '-', choice['name'], choice['publisher'], choice['year'] if 'year' in choice else '?'))
            i += 1
        if args.unattended:
            # use the first entry
            res = '1'
        else:
            # ask the user
            res = input('choose (1-%d): ' % (i - 1))

        # reissue with the correct entry
        c = e.choices()[int(res) - 1]
        print('Downloading data for "%s": %s, %s, %s' % (args.to_search, c['name'], c['publisher'], c['year']))
        game_info = engine.run_direct_url(c['url'], args)

    # check for append
    if args.append is not None:
        # append this string to name
        game_info['name'] += (' ' + args.append)

    if game_info['img_buffer'] is not None:
        # store image, ensuring folder exists
        try:
            os.mkdir(args.img_path)
        except FileExistsError:
            pass

        normalized = re.sub('[^0-9a-zA-Z]+', '-', game_info['name'])
        img_path = os.path.join(args.img_path, '%s.png' % normalized)
        vscraper_utils.write_to_file(img_path, game_info['img_buffer'])

        # add path to dictionary
        game_info['image'] = img_path
    else:
        game_info['image'] = None
    
    # add title path to dictionary
    game_info['path'] = args.path
     
    # create xml
    if os.path.exists(args.gamelist_path):
        # read existing
        xml = objectify.fromstring(vscraper_utils.read_from_file(args.gamelist_path))
    else:
        # create new
        xml = objectify.Element('gameList')

    # add entry
    if args.append_auto == 0:
        # single entry
        add_game_entry(args, xml, game_info)
    else:
        # add multiple entries
        idx = 1
        base_name = game_info['name']
        base_path = game_info['path']
        for idx in range (1, args.append_auto + 1):
            idx_str = str(idx)
            # generates a new path
            ext = os.path.splitext(base_path)[1];
            path_no_ext = os.path.splitext(base_path)[0];
            if idx < 10:
                dsk_path = path_no_ext[:-1] + idx_str
            else:
                dsk_path = path_no_ext[:-2] + idx_str

            new_path = dsk_path + ext
            game_info['path'] = new_path
            
            # generates a new name
            name = base_name
            name += (' (disk %s)' % idx_str)  
            game_info['name'] = name
            
            # add entry
            add_game_entry(args, xml,game_info)

    # rewrite
    print('Writing XML: %s' % args.gamelist_path)
    objectify.deannotate(xml)
    etree.cleanup_namespaces(xml)
    s = etree.tostring(xml, pretty_print=True)
    vscraper_utils.write_to_file(args.gamelist_path, s)

    print('Successfully processed "%s": %s (%s)' % (args.to_search, game_info['name'], args.path))
    if args.debug:
        # print debug result, avoid to print the image buffer if any
        if game_info['img_buffer'] is not None:
            game_info['img_buffer'] = '...'

        print(game_info)

def delete_entries(args):
    """
    delete one or more entries for gamelist xml, if they matches the specified regex
    """
    if not os.path.exists(args.gamelist_path):
        print('%s not found!' % args.gamelist_path)
        return

    # read xml
    xml = objectify.fromstring(vscraper_utils.read_from_file(args.gamelist_path))
    modified = 0    
    for game in xml.getchildren():
        for e in game.getchildren():
            if e.tag == 'path':
                match = re.match(args.delete, e.text, re.M|re.I)
                if match:
                    print('removing: %s (%s)' % (e.text,game.getchildren()[0]))
                    xml.remove(game)
                    modified = 1

    if modified == 0:
        print('Nothing to delete!')
        return

    # rewrite
    print('Writing XML: %s' % args.gamelist_path)
    objectify.deannotate(xml)
    etree.cleanup_namespaces(xml)
    s = etree.tostring(xml, pretty_print=True)
    vscraper_utils.write_to_file(args.gamelist_path, s)

def main():
    parser = argparse.ArgumentParser('Build gamelist.xml for EmulationStation by querying online databases\n')
    parser.add_argument('--list_engines', help="list the available engines (and their options, if any)", action='store_const', const=True)
    parser.add_argument('--engine', help="the engine to use (use --list_engines to check available engines)", nargs='?')
    parser.add_argument('--engine_params', help="custom engine parameters, name=value[,name=value,...], default None", nargs='?')
    parser.add_argument('--path', help='path to the file to be scraped', nargs='?')
    parser.add_argument('--to_search',
                        help='the game to search for (full or sub-string), case insensitive, enclosed in "" if containing spaces. Default is the filename part of path without extension',
                        nargs='?')
    parser.add_argument('--gamelist_path',
                        help='path to gamelist.xml (default path/gamelist.xml, will be created if not found or appended to)',
                        nargs='?')
    parser.add_argument('--img_path', help='path to the folder where to store images (default path/images)', nargs='?')
    parser.add_argument('--img_index',
                        help='download image at 0-based index among available images (default 0=first found, -1 tries to download boxart if found or fallbacks to first image found)',
                        nargs="?", type=int, default=0)
    parser.add_argument('--img_thumbnail',
                        help='download image thumbnail, if possible',
                        action='store_const', const=True)
    parser.add_argument('--append', help='append this string (enclosed in "" if containing spaces) to the game name in the gamelist.xml file', nargs='?')
    parser.add_argument('--append_auto', 
        help='automatically generate n entries starting from the given one (i.e. --append_auto 2 --path=./game1.d64 generates "game (disk 1)" pointing to ./game1.d64 and "game (disk 2)" pointing to ./game2.d64)', 
        type=int, default=0)  
    parser.add_argument('--unattended',
                        help='Automatically choose the first found entry in case of multiple entries found (default False, asks on multiple choices)',
                        action='store_const', const=True)
    parser.add_argument('--delete', help='delete all the entries whose path matches this regex from the gamelist.xml (needs --gamelist_path)', nargs='?')
    parser.add_argument('--relative_paths', help='put relative paths for images and game files in the gamelist.xml (./images/image.png and ./game.xxx)', action='store_const', const=True);
    parser.add_argument('--debug',
                        help='Print scraping result on the console',
                        action='store_const', const=True)
    args = parser.parse_args()
    if args.list_engines:
        # list engines and exit
        scrapers = list_scrapers()
        if len(scrapers) == 0:
            print('No scrapers installed. check ./scrapers folder!')
            exit(1)

        print('Available scrapers:')
        print('-----------------------------------------------------------------')
        for s in scrapers:
            print('scraper: %s' % s.name())
            print('url: %s' % s.url())
            print('supported system/s: %s' % s.systems())
            opts = s.engine_help()
            if opts is not None and opts != '':
                print('custom options:\n\t%s' % opts)
            print('-----------------------------------------------------------------')

        exit(0)
     
    if args.delete is not None and args.gamelist_path is None:
        print('--gamelist_path is required in delete mode')
        exit(1)

    if args.delete is None and (args.engine is None or args.path is None):
        print('--engine and --path are required!')
        exit(1)
       
    try:
        if args.delete is not None:
            # delete entries from xml
            delete_entries(args)
        else:
            # get module
            mod = get_scraper(args.engine)

            # scrape (single)
            scrape_title(mod, args)
    except Exception as e:
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
    exit(0)
