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

    return scrapers


def get_scraper(engine):
    """
    get the desired scraper
    :param engine: scraper name
    :return: module
    """
    path = os.path.join('./scrapers', engine)
    if not os.path.exists(path) or not os.path.exists(os.path.join(path, '%s.py' % engine)):
        raise FileNotFoundError('Scraper "%s" is not installed!' % engine)

    try:
        scraper = '%s.%s.%s' % (SCRAPERS_FOLDER, engine, engine)
        return importlib.import_module(scraper)
    except Exception as e:
        raise ImportError('Cannot import scraper "%s"' % engine)


def add_game_entry(root, game_info):
    """
    adds/replace an entry to the gamelist xml
    :param root: 'gameList' root entry
    :param game_info: a dictionary
    :return:
    """

    # check if game is already there
    game = None
    for g in root.findall('game'):
        if g.path == game_info['path']:
            # found, use this and replace content
            game = g;
            break

    if game is None:
        # create new entry
        game = objectify.Element('game')

    # fill values
    game.name = game_info['name']
    game.developer = game_info['developer']
    game.publisher = game_info['publisher']
    game.desc = game_info['desc']
    game.genre = game_info['genre']
    game.releasedate = game_info['releasedate']
    game.path = game_info['path']
    game.image = game_info['image']

    # append entry
    root.append(game)


def scrape_title(engine, args, cwd):
    """
    scrape a single title
    :param engine an engine module
    :param args dictionary
    :param cwd the saved working dir
    :return:
    """
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
            print('%s: [%s] %s, %s, %s' % (i, choice['system'] if 'system' in choice else '-',
                                           choice['name'], choice['publisher'], choice['year'] if 'year' in choice else '?'))
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

    # switch back to saved cwd
    os.chdir(cwd)

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
    add_game_entry(xml, game_info)

    # rewrite
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


def main():
    # change dir first to the script working dir
    _cwd = os.getcwd()
    os.chdir(sys.path[0])

    parser = argparse.ArgumentParser('Build gamelist.xml for EmulationStation by querying online databases\n')
    parser.add_argument('--list_engines', help="list the available engines (and their options, if any)", action='store_const', const=True)
    parser.add_argument('--engine', help="the engine to use (use --list_engines to check available engines)", nargs='?')
    parser.add_argument('--engine_params', help="custom engine parameters, name=value[,name=value,...], default None", nargs='?')
    parser.add_argument('--to_search',
                        help='the game to search for (full or sub-string), case insensitive, enclosed in " " (i.e. "game")',
                        nargs='?')
    parser.add_argument('--path', help='path to the single game file or path to games folder', nargs='?')
    parser.add_argument('--gamelist_path',
                        help='path to gamelist.xml (default "./gamelist.xml", will be created if not found or appended to)',
                        nargs='?',
                        default='./gamelist.xml')
    parser.add_argument('--img_path', help='path to the folder where to store images (default "./images")', nargs='?',
                        default='./images')
    parser.add_argument('--img_index',
                        help='download image at 0-based index among available images (default 0=first found, -1 tries to download boxart if found or fallbacks to first image found)',
                        nargs="?", type=int, default=0)
    parser.add_argument('--img_thumbnail',
                        help='download image thumbnail, if possible',
                        action='store_const', const=True)
    parser.add_argument('--unattended',
                        help='Automatically choose the first found entry in case of multiple entries found (default False, asks on multiple choices)',
                        action='store_const', const=True)
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
            print('custom options:\n\t%s' % s.engine_help())
            print('-----------------------------------------------------------------')

        exit(0)

    if args.engine is None or args.path is None:
        print('--engine and --path are required!')
        exit(1)

    try:
        # get module
        mod = get_scraper(args.engine)

        # scrape (single)
        scrape_title(mod, args, _cwd)
    except Exception as e:
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
    exit(0)
