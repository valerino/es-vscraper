#!/usr/bin/env python3
"""
es-vscraper

/MIT-LICENSE

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
import random
import time
import sys
import shutil
import vscraper_utils
from lxml import etree, objectify
from fuzzywuzzy import fuzz

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
    cwd = os.getcwd()
    os.chdir(sys.path[0])
    path = os.path.join('./scrapers', engine)
    if not os.path.exists(path) or not os.path.exists(
            os.path.join(path, '%s.py' % engine)):
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
        print('Creating entry: %s' % game_info['name'])
        game = objectify.Element('game')

    # fill values
    game.name = game_info['name']
    game.developer = game_info['developer']
    game.publisher = game_info['publisher']
    game.desc = game_info['desc'] or '-'
    game.genre = game_info['genre']
    game.releasedate = game_info['releasedate']
    game.path = os.path.abspath(game_info['path'])
    if game_info['image'] is not None:
        game.image = os.path.abspath(game_info['image'])

    # append entry
    root.append(game)


def scrape_move_delete(args):
    """
    move/delete unwanted/not scraped files during scraping
    """
    if args.dumpbin is not None:
        # rename/move
        os.makedirs(os.path.abspath(args.dumpbin), exist_ok=True)
        renamed = os.path.join(os.path.abspath(args.dumpbin),
                               os.path.basename(os.path.abspath(args.path)))
        shutil.move(args.path, renamed)
        print('Non-scraped file %s moved to: %s' % (args.path, renamed))
    else:
        # check for deletion
        if args.delete_no_scraped == True:
            os.remove(args.path)
            print('DELETED non-scraped file: %s' % (args.path))


def scrape_title(engine, args):
    """
    scrape a single title
    :param engine an engine module
    :param args dictionary
    :return: 0 on success, -1 on not found on disk, -2 on skip, -3 on not found on server
    """
    args.path = os.path.abspath(args.path)
    if not os.path.exists(args.path):
        print('%s not found!' % args.path)
        return -1

    if args.to_search is None:
        ts = args.path
        if args.trunc_at is not None:
            # truncate at the first occurrence of the given character/s
            l = re.match(('(.[^%s]+)' % re.escape(args.trunc_at)), os.path.basename(ts))
            args.to_search = l[0].strip()
        else:
            # to_search (name to be queried by scraper) is the filename without extension
            args.to_search = os.path.splitext(os.path.basename(ts))[0]

    if args.img_path is None:
        # use path/images as images path
        args.img_path = os.path.join(os.path.dirname(args.path), 'images')

    if args.gamelist_path is None:
        # use path/gamelist.xml as gamelist path
        args.gamelist_path = os.path.join(
            os.path.dirname(args.path), 'gamelist.xml')

    # check if the game is already listed in the gamelist_path
    if os.path.exists(args.gamelist_path):
        xml = objectify.fromstring(vscraper_utils.read_from_file(args.gamelist_path))
        for g in xml.findall('game'):
            if g.path == os.path.abspath(args.path) and args.overwrite is None:
                # if so, it must be skipped (not overwritten)
                print('Skipping entry (already present): %s, %s' % (g['name'], g.path))
                return -2

    try:
        print('Downloading data for "%s" (%s, system=%s)...' % (args.to_search, os.path.abspath(
            args.path), '-' if args.engine_params is None else args.engine_params))
        game_info = engine.run(args)
    except vscraper_utils.GameNotFoundException as e:
        print('Cannot find "%s", scraper="%s"' % (args.to_search, engine.name()))
        scrape_move_delete(args)
        return -3

    except vscraper_utils.MultipleChoicesException as e:
        print('Multiple titles found for "%s":' % args.to_search)
        i = 1
        for choice in e.choices():
            print('%s: [%s] %s, %s, %s' % (i, choice['system'] if 'system' in choice else '-',
                                           choice['name'], choice['publisher'], choice['year'] if 'year' in choice else '?'))
            i += 1

        # ask using timeout, if any
        timeout = int(args.unattended_timeout)
        res = vscraper_utils.input_with_timeout(
            'choose (1-%d, 0 to delete/move): ' % (i - 1), timeout)
        if res == '0':
            # delete/move
            scrape_move_delete(args)
            return -3

        elif res == '':
            # use the first entry
            res = '1'

        # reissue with the correct entry
        c = e.choices()[int(res) - 1]
        print('Downloading data for "%s": %s, %s, %s' %
              (args.to_search, c['name'], c['publisher'], c['year']))
        game_info = engine.run_direct_url(c['url'], args)

    # check for append
    if args.path_is_dir is True:
        # append commands only valid in single entry mode
        args.append = None
        args.append_auto = 0

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
        xml = objectify.fromstring(
            vscraper_utils.read_from_file(args.gamelist_path))
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
        for idx in range(1, args.append_auto + 1):
            idx_str = str(idx)
            # generates a new path
            ext = os.path.splitext(base_path)[1]
            path_no_ext = os.path.splitext(base_path)[0]
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
            add_game_entry(args, xml, game_info)

    # rewrite
    print('Writing XML: %s' % args.gamelist_path)
    objectify.deannotate(xml)
    etree.cleanup_namespaces(xml)
    s = etree.tostring(xml, pretty_print=True)
    vscraper_utils.write_to_file(args.gamelist_path, s)

    print('Successfully processed "%s": %s (%s)' %
          (args.to_search, game_info['name'], args.path))
    if args.debug:
        # print debug result, avoid to print the image buffer if any
        if game_info['img_buffer'] is not None:
            game_info['img_buffer'] = '...'

        print(game_info)

    return 0


def scrape_folder(mod, args):
    """
    scrape an entire folder, based on filenames
    """

    # get all files in folder
    args.path = os.path.abspath(args.path)
    files = os.listdir(args.path)
    tmp = args.path
    args.path_is_dir = True
    for f in files:
        if os.path.isdir(os.path.join(tmp, f)):
            # skip subfolders
            continue
        if f.lower() == 'gamelist.xml':
            # skip gamelist
            continue

        try:
            # process entry
            game_path = os.path.join(tmp, f)
            args.path = game_path
            args.to_search = None
            res = scrape_title(mod, args)
            if res == 0 or res == -3:
                # sleep between 1 and sleep (avoid hammering)
                seconds = random.randint(1, int(args.sleep))
                time.sleep(seconds)

        except Exception as e:
            # show error and continue
            traceback.print_exc()
            continue

    # done
    args.path = tmp


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
                match = re.match(args.purge, e.text, re.M | re.I)
                if match:
                    print('removing: %s (%s)' % (e.text, game.getchildren()[0]))
                    xml.remove(game)

                    # also try to delete file
                    try:
                        os.remove(e.text)
                    except Exception as e:
                        pass
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


def preprocess_duplicates_internal_move_delete_file(args, entry):
    """
    move or delete the file during duplicates preprocessing
    """
    if args.dumpbin is not None:
        # move
        moved_path = os.path.join(args.dumpbin, entry)
        src_path = os.path.join(args.path, entry)
        print('MOVING DUPLICATE: %s to %s\n' % (src_path, moved_path))
        if not args.preprocess_test:
            # actually move the file there
            shutil.move(src_path, moved_path)
    else:
        # delete
        print('DELETING DUPLICATE: %s\n' % src_path)
        if not args.preprocess_test:
            # actually delete the file
            os.unlink(src_path)


def preprocess_duplicates_internal(args, entry, files):
    """
    remove duplicates entries and return the purged list
    :param args the program args
    :param entry the current entry to check
    :param files the whole list
    :return: the processed list
    """
    l = []

    # add the main entry
    l.append(entry)

    # check this entry with all
    for f in files:
        if f == entry:
            # skip self
            continue

        # calculate ratio
        ratio = fuzz.QRatio(entry, f)
        if ratio > 95:
            l.append(f)
            # print('ratio=%d,s1=%s,s2=%s' % (ratio, entry, f))

    if len(l) == 1:
        # only one entry, ok
        return files

    print('Possible duplicates found:')
    i = 1
    for e in l:
        print('%d: %s' % (i, e))
        i += 1

    # ask using timeout, if any
    timeout = int(args.unattended_timeout)
    res = vscraper_utils.input_with_timeout(
        '\nA to keep all, 0 to delete all, or choose (1-%d) to delete (csv i.e. 1,2,3 accepted): ' % (i - 1), timeout)
    if (res == ''):
        # keep all
        res = 'A'

    if ',' in res:
        # more than one specified
        splitted = res.split(',')
        print(splitted)
        for s in splitted:
            # get entry
            to_delete = l[int(s) - 1]
            # remove from list
            files.remove(to_delete)
            # move or delete
            preprocess_duplicates_internal_move_delete_file(args, to_delete)
    elif res.lower() == 'a':
        # return all
        return files

    elif int(res) == 0:
        # delete all entries from list
        for s in l:
            # remove from list
            files.remove(s)
            # move or delete
            preprocess_duplicates_internal_move_delete_file(args, s)
    else:
        # only one specified, get entry
        to_delete = l[int(res) - 1]
        # remove from list
        files.remove(to_delete)
        # move or delete
        preprocess_duplicates_internal_move_delete_file(args, to_delete)

    # done
    return files


def preprocess_duplicates(args):
    """
    preprocess folder to remove duplicates
    """
    args.path = os.path.abspath(args.path)

    if args.dumpbin is not None:
        # create the move-to path
        os.makedirs(args.dumpbin, mode=0o777, exist_ok=True)

    # get all files in folder
    files = os.listdir(args.path)
    tmp = args.path

    # sort
    init_count = len(files)
    for f in files:
        if os.path.isdir(os.path.join(tmp, f)):
            # skip subfolders
            continue

        if f.lower() == 'gamelist.xml':
            # skip gamelist
            continue

        try:
            # process entry
            files = preprocess_duplicates_internal(args, f, files)
        except Exception as e:
            # show error and continue
            traceback.print_exc()
            continue

    print('done, processed %d files, cleaned up to %d in %s !' %
          (init_count, len(files), args.path))


def preprocess(args):
    """
    preprocess folder to delete unneeded files
    """
    args.path = os.path.abspath(args.path)

    if args.dumpbin is not None:
        if args.preprocess_test is not True:
            # create the move-to path
            os.makedirs(args.dumpbin, mode=0o777, exist_ok=True)

    # get all files in folder
    files = os.listdir(args.path)
    tmp = args.path
    args.path_is_dir = True
    count = 0
    tot = 0
    for f in files:
        if os.path.isdir(f):
            # skip subfolders
            continue

        if f.lower() == 'gamelist.xml':
            # skip gamelist
            continue

        try:
            # process entry
            match = re.match(args.preprocess, f, re.I)
            game_path = os.path.join(tmp, f)
            tot += 1
            if match is not None:
                print('MATCHING, %s' % game_path)
            else:
                # not MATCHING
                if args.dumpbin:
                    renamed = os.path.join(args.dumpbin, f)
                    count += 1
                    if args.preprocess_test is not True:
                        # rename/move
                        shutil.move(game_path, renamed)
                    print('NOT MATCHING, %s, moved to %s' % (game_path,
                                                             renamed))
                else:
                    print('NOT MATCHING, %s, deleting' % (game_path))
                    count += 1
                    if args.preprocess_test is not True:
                        # delete
                        os.remove(game_path)
        except Exception as e:
            # show error and continue
            traceback.print_exc()
            continue

    print('done, moved/deleted %d files (out of %d) in %s !' % (count, tot,
                                                                args.path))


def main():
    parser = argparse.ArgumentParser(
        'Manage games collection and build gamelist.xml by querying online databases\n'
    )
    parser.add_argument(
        '--list_engines',
        help="list the available engines (and their options, if any)",
        action='store_const',
        const=True)
    parser.add_argument(
        '--engine',
        help="the engine to use (use \'--list_engines\' to check available engines)",
        nargs='?')
    parser.add_argument(
        '--engine_params',
        help="custom engine parameters, name=value[,name=value,...], default None",
        default=None,
        nargs='?')
    parser.add_argument(
        '--path',
        help='path to the file to be scraped (needs to specify \'--to_search\'), or to a folder with (correctly named) files to be scraped',
        nargs='?')
    parser.add_argument(
        '--to_search',
        help='name of the game to search for enclosed in \'\' if containing spaces, the more accurate the better. Default is the filename at \'--path\' without extension. Ignored if \'--path\' refers to a folder',
        nargs='?',
        metavar='NAME',
        default=None)
    parser.add_argument(
        '--delete_no_scraped',
        help='delete non-scraped files, ignored if \'--dumpbin\' is specified',
        action='store_const',
        const=True)
    parser.add_argument(
        '--sleep',
        help='sleep random seconds (1..SECONDS) between each scraped entries when path refers to a folder. Default is 15',
        metavar='SECONDS',
        nargs='?',
        default=15)
    parser.add_argument(
        '--trunc_at',
        help='before using \'--path\' as search key, truncate at the first occurrence of any of the given characters (i.e. --path \'./caesar the cat, (demo) (eng).zip\' --trunc_at \'(,\' searches for \'caesar the cat\')',
        metavar='CHARACTERS',
        nargs='?')
    parser.add_argument(
        '--gamelist_path',
        help='path to gamelist.xml (default \'<path>/gamelist.xml\', will be created if not found or appended to)',
        nargs='?')
    parser.add_argument(
        '--overwrite',
        help='existing entries in gamelist.xml will be overwritten. Default is to skip existing entries',
        action='store_const',
        const=True)
    parser.add_argument(
        '--img_path',
        help='path to the folder where to store images (default \'<path>/images)\'',
        nargs='?')
    parser.add_argument(
        '--img_index',
        help='download image at 0-based index among available images (default 0=first found, -1 tries to download boxart if found or fallbacks to first image found)',
        nargs='?',
        type=int,
        default=0)
    parser.add_argument(
        '--img_thumbnail',
        help='download image thumbnail (support depends on the scraper engine)',
        action='store_const',
        const=True)
    parser.add_argument(
        '--append',
        help='append this string (enclosed in \'\' if containing spaces) to the game name in the gamelist.xml file. Only valid if \'--path\' do not refer to a folder',
        metavar='STRING',
        nargs='?')
    parser.add_argument(
        '--append_auto',
        help='automatically generate n entries starting from the given one (i.e. --append_auto 2 --path=./game1.d64 generates \'game (disk 1)\' pointing to ./game1.d64 and \'game (disk 2)\' pointing to ./game2.d64). Only valid if \'--path\' do not refer to a folder',
        metavar='N',
        type=int,
        default=0)
    parser.add_argument(
        '--unattended_timeout',
        help='automatically choose the first found entry after the specified seconds, in case of multiple entries found (default is to ask on multiple choices)',
        nargs='?',
        metavar='SECONDS',
        default=0)
    parser.add_argument(
        '--dumpbin',
        help='move non-scraped, not matching from \'--preprocess\' or duplicates from \'--preprocess_duplicates\' files to this path if specified',
        metavar='PATH',
        nargs='?')
    parser.add_argument(
        '--purge',
        help='delete all the entries whose path matches the given regex from the gamelist.xml (needs \'--gamelist_path\', anything else is ignored). This also deletes the affected game files!',
        metavar='REGEX',
        nargs='?')
    parser.add_argument(
        '--preprocess',
        help='preprocess folder at \'--path\' and keep only the files matching the given regex (every other parameter is ignored). This cleans the directory for later processing by the scraper',
        metavar='REGEX',
        nargs='?')
    parser.add_argument(
        '--preprocess_duplicates',
        help='check for duplicates (and ask for deletion or moving to \'--dumpbin\' if specified)',
        action='store_const',
        const=True)
    parser.add_argument(
        '--preprocess_test',
        help='test for preprocessing options, do not delete/move files',
        action='store_const',
        const=True)
    parser.add_argument(
        '--debug',
        help='Print scraping result on the console',
        action='store_const',
        const=True)
    args = parser.parse_args()
    if args.list_engines:
        # list engines and exit
        scrapers = list_scrapers()
        if len(scrapers) == 0:
            print('No scrapers installed. check ./scrapers folder!')
            exit(1)

        print('Available scrapers:')
        print(
            '-----------------------------------------------------------------')
        for s in scrapers:
            print('scraper: %s' % s.name())
            print('url: %s' % s.url())
            print('supported system/s: %s' % s.systems())
            opts = s.engine_help()
            if opts is not None and opts != '':
                print('custom options:\n\t%s' % opts)
            print(
                '-----------------------------------------------------------------'
            )

        exit(0)

    if args.preprocess is not None and args.path is None:
        print('--path is required for --preprocess')
        exit(1)
    if args.preprocess_duplicates is not None and args.path is None:
        print('--path is required for --preprocess_duplicates')
        exit(1)
    if args.preprocess is not None and args.preprocess_duplicates is not None:
        print(
            '--preprocess and --preprocess_duplicates are mutually exclusive'
        )
        exit(1)
    if args.preprocess is None and args.purge is not None and args.gamelist_path is None:
        print('--gamelist_path is required for --purge')
        exit(1)

    if args.preprocess is None and args.preprocess_duplicates is None and args.purge is None and (
            args.engine is None or args.path is None):
        print('--engine and --path are required, use --help for options')
        exit(1)
    try:
        if args.preprocess_duplicates is not None:
            preprocess_duplicates(args)
        elif args.preprocess is not None:
            # preprocess path
            preprocess(args)
        elif args.purge is not None:
            # delete entries from xml
            delete_entries(args)
        else:
            # get module
            mod = get_scraper(args.engine)

            if os.path.isdir(args.path):
                # scrape entire folder
                scrape_folder(mod, args)
            else:
                # scrape single file
                args.path_is_dir = False
                scrape_title(mod, args)

    except Exception as e:
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
    exit(0)
