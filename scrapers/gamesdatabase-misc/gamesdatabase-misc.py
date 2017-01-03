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


def _find_full_img_tag(tag):
    if tag.name == 'img' and tag.has_attr('alt') and 'Artwork' in tag['alt']:
        return True
    return False


def _find_ingame_thumb_tag(tag):
    if tag.name == 'img' and tag.has_attr('alt') and tag['alt'].startswith('In game image '):
        return True
    return False


def _find_title_thumb_tag(tag):
    if tag.name == 'img' and tag.has_attr('alt') and tag['alt'].startswith('Title screen '):
        return True
    return False


def _find_box_thumb_tag(tag):
    if tag.name == 'img' and tag.has_attr('alt') and tag['alt'].startswith('Box cover '):
        return True
    return False


def _find_a_text_box(tag):
    if tag.name == 'a' and tag.text == 'Box':
        return True
    return False


def _find_a_text_ingame(tag):
    if tag.name == 'a' and tag.text == 'In Game':
        return True
    return False


def _find_a_text_title(tag):
    if tag.name == 'a' and tag.text == 'Title Screen':
        return True
    return False


def _download_image(soup, args):
    """
    download game image
    :param soup: the source soup
    :param machine: the system
    :param args: arguments from cmdline
    :return: image buffer, or None
    """

    got_cover = False
    img_url = ''

    if args.img_cover:
        # download cover
        try:
            if args.img_thumbnail:
                # thumbnail
                img_url = 'http://www.gamesdatabase.org%s' % soup.find(_find_box_thumb_tag)['src']
            else:
                # full
                href = 'http://www.gamesdatabase.org%s' % soup.find(_find_a_text_box)['href']
                reply = requests.get(href)
                html = reply.content
                s = BeautifulSoup(html, 'html.parser')
                img_url = 'http://www.gamesdatabase.org%s' % s.find(_find_full_img_tag)['src']

            got_cover = True
        except Exception as e:
            pass

    try:
        if not got_cover:
            if args.img_index == 0:
                # try to get ingame
                if args.img_thumbnail:
                    # thumbnail
                    img_url = 'http://www.gamesdatabase.org%s' % soup.find(_find_ingame_thumb_tag)['src']
                else:
                    # full
                    href = 'http://www.gamesdatabase.org%s' % soup.find(_find_a_text_ingame)['href']
                    reply = requests.get(href)
                    html = reply.content
                    s = BeautifulSoup(html, 'html.parser')
                    img_url = 'http://www.gamesdatabase.org%s' % s.find(_find_full_img_tag)['src']
            else:
                # try to get title
                if args.img_thumbnail:
                    # thumbnail
                    img_url = 'http://www.gamesdatabase.org%s' % soup.find(_find_title_thumb_tag)['src']
                else:
                    # full
                    href = 'http://www.gamesdatabase.org%s' % soup.find(_find_a_text_title)['href']
                    reply = requests.get(href)
                    html = reply.content
                    s = BeautifulSoup(html, 'html.parser')
                    img_url = 'http://www.gamesdatabase.org%s' % s.find(_find_full_img_tag)['src']

        # download
        reply = requests.get(img_url)
        img = reply.content

        # convert to png
        img_buffer = vscraper_utils.img_to_png(img)
        return img_buffer

    except Exception as e:
        return None


def run_direct_url(u, args):
    """
    perform query with the given direct url
    :param u: the game url
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
        if args.engine_params is not None:
            # handle multi-disk
            p = vscraper_utils.get_parameter(args.engine_params, 'disk_num')
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
    machine = vscraper_utils.get_parameter(args.engine_params, 'system')
    game_info['img_buffer'] = _download_image(soup, args)

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


def run(args):
    """
    perform query with the given game title
    :param args: arguments from cmdline
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each may be empty)
    """
    if args.engine_params is None:
        print(
            '--engine_params system=... is required (use --list_engines to check supported systems for %s scraper' % name())
        raise ValueError

    # get system
    s = vscraper_utils.get_parameter(args.engine_params, 'system')

    # normalize game name
    game = re.sub('[^0-9a-zA-Z]+', '-', args.to_search)
    game = game.replace('--', '-')

    # get url
    u = 'http://www.gamesdatabase.org/game/%s/%s' % (s, game)

    # reissue
    return run_direct_url(u, args)


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


def systems():
    """
    the related system/s
    :return: string (i.e. 'Commodore 64')
    """
    return """acorn-archimedes,acorn-atom,acorn-bbc-micro,acorn-electron,amstrad-cpc,amstrad-gx4000,apple-ii,arcade,atari-2600,atari-5200,atari-7800,
        atari-8-bit,atari-jaguar,atari-jaguar-cd,atari-lynx,atari-st,bally-astrocade,bandai-wonderswan,bandai-wonderswan-color,casio-loopy,casio-pv-1000,
        coleco-vision,commodore-128,commodore-64,commodore-amiga,commodore-amiga-cd32,commodore-cdtv,commodore-pet,commodore-vic-20,dragon-32-64,emerson-arcadia-2001,
        entex-adventure-vision,epoch-super-cassette-vision,fairchild-channel-f,funtech-super-acan,gamepark-gp32,gce-vectrex,genesis-microchip-nuon,hartung-game-master,
        interton-vc-4000,laserdisc,magnavox-odyssey,magnavox-odyssey-2,mattel-intellivision,mega-duck,memotech-mtx,mgt-sam-coupe,microsoft-xbox,microsoft-xbox-360,
        microsoft-xbox-live-arcade,msx,msx-2,msx-2+,msx-laserdisc,mugen,nec-pc-engine,nec-pc-engine-cd,nec-pc-fx,nec-supergrafx,nec-turbografx-cd,nec-turbografx-16,nintendo-arcade-systems,
        nintendo-ds,nintendo-famicom-disk-system,nintendo-game-boy,nintendo-game-boy-advance,nintendo-game-boy-color,nintendo-gamecube,nintendo-n64,nintendo-nes,nintendo-pokemon-mini,
        nintendo-snes,nintendo-super-gameboy,nintendo-virtual-boy,nintendo-wii,openbor,panasonic-3do,philips-cd-i,philips-vg-5000,philips-videopac+,popcap,rca-studio-ii,sammy-atomiswave,
        scummvm,sega-32x,sega-cd,sega-dreamcast,sega-game-gear,sega-genesis,sega-master-system,sega-model-2,sega-model-3,sega-naomi,sega-nomad,sega-pico,sega-saturn,sega-sc-3000,sega-sg-1000,
        sega-st-v,sinclair-zx-spectrum,sinclair-zx-81,snk-neo-geo-aes,snk-neo-geo-cd,snk-neo-geo-mvs,snk-neo-geo-pocket,snk-neo-geo-pocket-color,sony-playstation,sony-playstation-2,sony-psp,
        sord-m5,taito-type-x,taito-type-x2,tandy-trs-80,tandy-trs-80-coco,tangerine-oric,texas-instruments-ti-99/4a,tiger-game.com,touhou-project,valve-steam,vtech-creativision,
        watara-supervision,wow-action-max"""


def engine_help():
    """
    help on engine specific '--engine_params' and such
    :return: string
    """
    return """disk_num=n (set disk number)
        system=name (scrape this system)
        note: img_index=0 (default) downloads in-game screen, img_index=1 downloads title screen"""
