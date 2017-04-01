"""
es-vscraper module for http://atariage.com

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
import urllib
import vscraper_utils


def _find_a_text_softwareLabelID(tag):
    if tag.name == 'a' and ('SoftwareLabelID' in tag['href']) and (not tag.has_attr('title')):
        return True
    return False

def _find_b_text_year(tag):
    if tag.name == 'b' and (tag.text.startswith('Year of Release')):
        return True
    return False

def _find_a_text_companyID(tag):
    if tag.name == 'a' and ('CompanyID' in tag['href']):
        return True
    return False

def _find_a_text_programmerID(tag):
    if tag.name == 'a' and ('ProgrammerID' in tag['href']):
        return True
    return False

def _download_image(soup, args):
    """
    download game image
    :param soup: the source soup
    :param args: arguments from cmdline
    :return: image buffer, or None
    """
    img_url = ''
    got_cover = False

    if args.img_index == -1:
        # try to get boxart
        try:
            covers = vscraper_utils.find_href(soup, 'https://atariage.com/box_page.php?')
            cover_url = covers[0]['href']
            reply = requests.get(cover_url)
            html = reply.content
            s = BeautifulSoup(html, 'html.parser')
            img_urls = s.find_all('img')
            for i in img_urls:
                if '/boxes/' in i['src']:
                    # found, get first
                    img_url = i['src']
                    got_cover = True
                    break
        except Exception as e:
            # fallback to 0
            args.img_index = 0
            pass

    try:
        if not got_cover:
            # get screenshots
            scrs = vscraper_utils.find_href(soup, 'https://atariage.com/screenshot_page.php?')
            scrs_url = scrs[0]['href']
            reply = requests.get(scrs_url)
            html = reply.content
            s = BeautifulSoup(html, 'html.parser')
            img_urls = s.find_all('img')
            screens =[]
            for s in img_urls:
                if '/screenshots/' in s['src']:
                    screens.append(s)
            try:
                img_url=screens[args.img_index]['src']
            except:
                img_url=screens[0]['src']

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
    :param args: arguments from cmdline
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each except 'name' may be empty)
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

    # name
    game_info['name'] = soup.find('span', {'class': 'gametitle'}).text

    # publisher
    game_info['publisher'] = soup.find(_find_a_text_companyID).text

    # releasedate
    game_info['releasedate'] = vscraper_utils.get_text_no_tags(soup.find(_find_b_text_year).parent, 'b').strip()

    # developer
    devs = soup.find_all(_find_a_text_programmerID)
    d = ''
    for dev in devs:
        # may be more than one dev....
        d += (dev.text + ',')

    if len(d) >=1:
        # zap last ,
        d = d[:-1]
        game_info['developer'] = d
    else:
        # not found
        game_info['developer'] = ''

    # genre
    game_info['genre'] = ''

    # description
    game_info['desc'] = ''
    bh = soup.find_all('td', {'class': 'bodyheader'})
    for b in bh:
        if b.text == 'Description':
            body = b.parent.parent.find('td',{'class':'bodytext'})
            if body is not None:
                game_info['desc'] = body.text.strip()

    # image
    game_info['img_buffer'] = _download_image(soup, args)

    return game_info


def _check_response(reply):
    """
    check server response (not found, single, multi)
    :param reply: the server reply
    :throws vscraper_utils.GameNotFoundException when a game is not found
    :return: [{name,publisher,year,url}] (each except 'name' may be empty)
    """
    html = reply.content
    soup = BeautifulSoup(html, 'html.parser')

    # check validity
    all_games = soup.find_all(_find_a_text_softwareLabelID)
    games = []
    for g in all_games:
        entry = {}
        entry['name'] = g.text.strip()
        entry['year'] = 'n/a'
        entry['publisher'] = g.parent.findNext('td').findNext('a').text
        entry['url'] = g['href']
        games.append(entry)

    if len(games) is 0:
        # not found
       raise vscraper_utils.GameNotFoundException

    return games


def run(args):
    """
    perform query with the given game title
    :param args: arguments from cmdline
    :throws vscraper_utils.GameNotFoundException when a game is not found
    :throws vscraper_utils.MultipleChoicesException when multiple choices are found. ex.choices() returns [{ name, publisher, year, url, system}] (each except 'name' may be empty)
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each except 'name' may be empty)
    """
    if args.engine_params is None:
        print(
            '--engine_params system=... is required (use --list_engines to check supported systems)')
        raise ValueError

    # get system
    engines = {'2600', '5200', '7800', 'lynx', 'jaguar'}
    s = vscraper_utils.get_parameter(args.engine_params, 'system')
    if s not in engines:
        print('supported systems: %s' % engines)
        raise ValueError

    # get game id
    params = {'searchValue': args.to_search, 'SystemID': s, 'searchType':'NORMAL', 'searchShot':'checkbox', 'searchBox':'checkbox', 'orderBy':'Name'}
    u = 'https://atariage.com/software_list.php'
    reply = requests.get(u, params=params)

    # check response
    if not reply.ok:
        raise ConnectionError

    choices = _check_response(reply)
    if len(choices) > 1:
        # return to es-vscraper with a multi choice
        raise vscraper_utils.MultipleChoicesException(choices)

    # got single response, reissue
    return run_direct_url(choices[0]['url'], args)


def name():
    """
    the plugin name
    :return: string (i.e. 'lemon64')
    """
    return 'atariage-atari'


def url():
    """
    the plugin url name
    :return: string (i.e. 'http://www.lemon64.com')
    """
    return 'http://atariage.com'


def systems():
    """
    the related system/s
    :return: string (i.e. 'Commodore 64')
    """
    return 'Atari 2600, 5200, 7800, Lynx, Jaguar'


def engine_help():
    """
    help on engine specific '--engine_params' and such
    :return: string
    """
    return """system=name: specifies target system ('2600', '5200', '7800', 'lynx', 'jaguar')
        note: thumbnails not available"""
