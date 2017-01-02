"""
es-vscraper module for http://www.gamesdatabase.org

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

import re

import requests
from bs4 import BeautifulSoup
import vscraper_utils


def _get_real_img_url(soup, path):
    """
    get the real image url
    :param soup: the source soup
    :param path: path from source page
    :return: string or ''
    """
    u = vscraper_utils.find_href(soup, path)[0]['href']
    reply = requests.get('http://www.gamesdatabase.org%s' % u)
    html = reply.content
    s = BeautifulSoup(html, 'html.parser')
    imgs = s.find_all('img')
    for i in imgs:
        if 'alt' in i.attrs and 'Artwork' in i.attrs['alt']:
            img_url = 'http://www.gamesdatabase.org%s' % i.attrs['src']
            return img_url

    return ''

def _download_image(soup, machine, img_index=0, img_cover=False):
    """
    download game image
    :param soup: the source soup
    :param machine: the system
    :param img_index: image index, or 0
    :param img_cover: True to download cover
    :return: image buffer, or None
    """
    try:
        got_cover = False
        img_url = ''
        if img_cover:
            try:
                # get cover url
                box = '/media/%s/artwork-box' % machine
                img_url = _get_real_img_url(soup, box)
                if len(img_url) > 0:
                    got_cover = True
            except Exception as e:
                pass

        if not got_cover:
            in_game = '/media/%s/artwork-in-game' % machine
            title = '/media/%s/artwork-title-screen' % machine

            # for img_index = 0, we try to download title image, else we try ingame image
            try:
                img_url = _get_real_img_url(soup, title if img_index == 0 else in_game)
            except:
                # try the other way
                try:
                    img_url = _get_real_img_url(soup, in_game if img_index == 0 else title)
                except:
                    # no luck
                    return None

        # download
        reply = requests.get(img_url)
        img = reply.content

        # convert to png
        img_buffer = vscraper_utils.img_to_png(img)
        return img_buffer

    except Exception as e:
        return None


def run_direct_url(u, img_index=0, img_cover=False, engine_params=None):
    """
    perform query with the given direct url
    :param u: the game url
    :param img_index: 0-based index of the image to download, default 0
    :param img_cover: True to download boxart cover as image, default False. If boxart is not available, the first image found is used
    :param engine_params: engine params (name=value[,name=value,...]), default None
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each may be empty)
    """
    # issue request
    reply = requests.get(u)
    if not reply.ok:
        raise ConnectionError

    game_info = {}

    # got game page
    html = reply.content

    # parse
    soup = BeautifulSoup(html, 'html.parser')

    try:
        # name
        container = soup.find('span', id='Out')
        idx = container.contents[0].text.find(' - ')
        game_info['name'] = container.contents[0].text[:idx]
        if engine_params is not None:
            # handle multi-disk
            p = vscraper_utils.get_parameter(engine_params, 'disk_num')
            if len(p) > 0:
                game_info['name'] = vscraper_utils.add_disk(game_info['name'], p)
    except:
        raise vscraper_utils.GameNotFoundException

    # publisher
    vscraper_utils.add_text_from_href(container, '/all_publisher_games', game_info, 'publisher')

    # releasedate
    vscraper_utils.add_text_from_href(container, '/year-', game_info, 'releasedate')

    # developer
    vscraper_utils.add_text_from_href(container, '/all_developer_games', game_info, 'developer')

    # genre
    vscraper_utils.add_text_from_href(container, '/category-', game_info, 'genre')

    # description
    t = container.find('table', width='90%')
    if t is not None:
        game_info['desc'] = t.text.strip()
    else:
        game_info['desc'] = ''

    # image
    machine = vscraper_utils.get_parameter(engine_params, 'system')
    game_info['img_buffer'] = _download_image(soup, machine, img_index, img_cover)

    return game_info


def _check_response(reply):
    """
    check server response (not found, single, multi)
    :param reply: the server reply
    :return: [{name,publisher,year,url}] or throws GameNotFoundException
    """
    html = reply.content
    soup = BeautifulSoup(html, 'html.parser')

    # check validity
    games = soup.find_all('div', 'ginfo')
    if len(games) is 0 and soup.find('td', class_='normalheadblank') is None:
        # not found
        raise vscraper_utils.GameNotFoundException

    choices = []
    if len(games) is not 0:
        # build a list of all and return MultiChoicesException
        for g in games:
            entry = {}
            entry['name'] = vscraper_utils.find_href(g, 'details.php')[0].text
            entry['url'] = 'http://www.lemon64.com/games/%s' % (vscraper_utils.find_href(g, 'details.php')[0]['href'])
            vscraper_utils.add_text_from_href(g, '?year', entry, 'year')
            vscraper_utils.add_text_from_href(g, '?publisher', entry, 'publisher')
            choices.append(entry)
        return choices

    # single entry
    choices.append({"url": reply.url})
    return choices


def run(to_search, img_index=0, img_cover=False, engine_params=None):
    """
    perform query with the given game title
    :param to_search: the game title
    :param img_index: 0-based index of the image to download, default 0
    :param img_cover: True to download boxart cover as image, default False. If boxart is not available, the first image found is used
    :param engine_params: engine params (name=value[,name=value,...]), default None
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each may be empty)
    """
    if engine_params is None:
        print(
            '--engine_params system=... is required (use --list_engines to check supported systems for %s scraper' % name())
        raise ValueError

    # get system
    s = vscraper_utils.get_parameter(engine_params, 'system')

    # normalize game name
    game = re.sub('[^0-9a-zA-Z]+', '-', to_search)
    game = game.replace('--', '-')

    # get url
    u = 'http://www.gamesdatabase.org/game/%s/%s' % (s, game)

    # reissue
    return run_direct_url(u, img_index, img_cover, engine_params)


def name():
    """
    the plugin name
    :return: string (i.e. 'lemon64')
    """
    return 'gamesdatabase-misc'


def url():
    """
    the plugin url name
    :return: string (i.e. 'http://www.lemon64.com')
    """
    return 'http://www.gamesdatabase.org'


def system():
    """
    the related system (descriptive)
    :return: string (i.e. 'Commodore 64')
    """
    return 'Various'


def system_short():
    """
    the related system (short)
    :return: string (i.e. 'c64')
    """
    return 'misc'


def engine_help():
    """
    engine specific options to be used with '--engine_params'
    :return: string
    """
    return 'disk_num=n (set disk number),system=amstrad-cpc|apple-ii|atari-8-bit|atari-st|commodore-64|commodore-amiga|microsoft-xbox|msx|msx-2|nintendo-gameboy|nintendo-gameboy-color|nintendo-nes|sega-master-system|sinclair-zx-spectrum|sony-playstation-ii (the target system)'
