#!/usr/bin/env python3
# needs pip3 (sudo apt-get install python3-pip)
# needs requests, Image, bs4, lxml (sudo pip3 install requests Image bs4 lxml)

import argparse
import importlib
import os
import traceback

import vscraper_utils
from lxml import etree, objectify

SCRAPERS_FOLDER = 'scrapers'


def get_scrapers():
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


def scrape_title(engine, args):
    """
    scrape a single title
    :param engine an engine module
    :param args dictionary
    :return:
    """
    try:
        print('Downloading data for %s' % args.to_search)
        game_info = engine.run(args.to_search, args.img_index, args.img_cover)
    except vscraper_utils.GameNotFoundException as e:
        print('Cannot find %s on %s' % (args.to_search, engine.name()))
        raise e

    except vscraper_utils.MultipleChoicesException as e:
        print('Multiple titles found for %s:' % args.to_search)
        i = 1
        for choice in e.choices():
            print('%s: %s, %s, %s' % (i, choice['name'], choice['publisher'], choice['year']))
            i += 1
        if args.unattended:
            # use the first entry
            res = '1'
        else:
            # ask the user
            res = input('choose (1-%d): ' % (i - 1))

        # reissue with the correct entry
        c = e.choices()[int(res) - 1]
        print('Downloading data for %s: %s, %s, %s' % (args.to_search, c['name'], c['publisher'], c['year']))
        game_info = engine.run_direct_url(c['url'], args.img_index, args.img_cover)

    if game_info['img_buffer'] is not None:
        # store image, ensuring folder exists
        try:
            os.mkdir(args.img_path)
        except FileExistsError:
            pass
        img_path = os.path.join(args.img_path, '%s.png' % game_info['name'])
        vscraper_utils.write_to_file(img_path, game_info['img_buffer'])

        # add path to dictionary
        game_info['image'] = img_path

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
    print(game_info)


def main():
    parser = argparse.ArgumentParser('Build gamelist.xml for EmulationStation by querying online databases\n')
    parser.add_argument('--list_engines', help="list the available engines", action='store_const', const=True)
    parser.add_argument('--engine', help="the engine to use (use --list_engines to check available engines)", nargs='?')
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
                        help='download image at 0-based index among available images (default 0, first found)',
                        nargs="?", type=int, default=0)
    parser.add_argument('--img_cover',
                        help='try to download boxart cover if available, either it will download the first image found',
                        action='store_const', const=True)
    parser.add_argument('--unattended',
                        help='Always choose the first found entry in case of multiple entries found (default False, asks on multiple choices)',
                        action='store_const', const=True)
    args = parser.parse_args()
    if args.list_engines:
        # list engines and exit
        scrapers = get_scrapers()
        if len(scrapers) == 0:
            print('No scrapers installed. check ./scrapers folder!')
            exit(1)

        print('Available scrapers:')
        for s in scrapers:
            print('%s (System: %s (%s), url: %s)' % (s.name(), s.system(), s.system_short(), s.url()))
        exit(0)

    if args.engine is None or args.path is None:
        print('--engine and --path are required!')
        exit(1)

    try:
        # get module
        mod = get_scraper(args.engine)

        # scrape (single)
        scrape_title(mod, args)
    except:
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
    exit(0)
