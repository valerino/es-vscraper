"""
es-vscraper module for http://www.lemon64.com

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


def _download_image(soup, args):
    """
    download game image
    :param soup: the source soup
    :param args: arguments from cmdline
    :return: image buffer, or None
    """
    got_cover = False
    img_url = ''

    if args.img_cover:
        try:
            if not args.img_thumbnail:
                # prefer full size, get cover url
                r = re.search('(.+=)([0-9]+)', soup.find('link', rel='canonical').attrs['href'])
                gameid = r.group(2)
                u = 'http://www.lemon64.com/games/view_cover.php?gameID=%s' % gameid
                reply = requests.get(u)
                html = reply.content
                s = BeautifulSoup(html, 'html.parser')
                img_url = s.find('img').attrs['src']
            else:
                # thumbnail
                img_url = soup.find('img', {'name': 'imgCover'})['src']

            got_cover = True
        except Exception as e:
            pass

    try:
        if not got_cover:
            # get screenshot url, no thumbnail is available here
            img_urls = soup.find_all('img', 'pic')
            selected_img = img_urls[args.img_index]
            img_url = selected_img.attrs['src']

        # download
        reply = requests.get(img_url)
        img = reply.content

        # convert to png
        img_buffer = vscraper_utils.img_to_png(img)
        return img_buffer

    except Exception as e:
        return None


def _download_descr(soup):
    """
    download description/review
    :param soup: the html
    :return: description/review
    """

    # search for review / description
    try:
        review_url = vscraper_utils.find_href(soup, '/reviews/view.php')[0]['href']
        reply = requests.get('http://www.lemon64.com%s' % review_url)

        # got review page
        html = reply.content

        # parse desc
        s = BeautifulSoup(html, 'html.parser')
        descr = s.find('td', 'tablecolor').text.strip()
        descr = descr[:descr.rfind('Downloads:')]
        return descr
    except:
        # no review, try comments
        try:
            r = re.search('(.+=)([0-9]+)', soup.find('link', rel='canonical').attrs['href'])
            gameid = r.group(2)
            reply = requests.get('http://www.lemon64.com/games/comments/text.php?gameID=%s' % gameid)
            html = reply.content
            s = BeautifulSoup(html, 'html.parser')
            tds = s.find_all(target='content')
            descr = tds[0].next_sibling.next_sibling.text.strip()
            return descr
        except:
            return ''


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
    container = soup.find('td', class_='normalheadblank')
    game_info['name'] = container.contents[1].text.strip()
    if args.engine_params is not None:
        # handle multi-disk
        p = vscraper_utils.get_parameter(args.engine_params, 'disk_num')
        if len(p) > 0:
            game_info['name'] = vscraper_utils.add_disk(game_info['name'], p)

    # publisher
    vscraper_utils.add_text_from_href(soup, 'list.php?publisher', game_info, 'publisher')

    # releasedate
    vscraper_utils.add_text_from_href(soup, 'list.php?year', game_info, 'releasedate')

    # developer
    vscraper_utils.add_text_from_href(soup, 'list.php?coder', game_info, 'developer')
    if game_info['developer'] == '':
        vscraper_utils.add_text_from_href(soup, 'list.php?developer', game_info, 'developer')

    # genre
    vscraper_utils.add_text_from_href(soup, 'list.php?genre', game_info, 'genre')

    # description
    game_info['desc'] = _download_descr(soup)

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
    games = soup.find_all('div', 'ginfo')
    if len(games) is 0 and soup.find('td', class_='normalheadblank') is None:
        # not found
        raise vscraper_utils.GameNotFoundException

    choices = []
    if len(games) is not 0:
        # build a list of all and return MultiChoicesException
        for g in games:
            entry = {}
            entry['name']= vscraper_utils.find_href(g, 'details.php')[0].text
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
    :throws vscraper_utils.GameNotFoundException when a game is not found
    :throws vscraper_utils.MultipleChoicesException when multiple choices are found. ex.choices() returns [{ name, publisher, year, url, system}] (each except 'name' may be empty)
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each except 'name' may be empty)
    """
    # get game id
    params = {'type': 'title', 'name': args.to_search}
    u = 'http://www.lemon64.com/games/list.php'
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
    return 'lemon-64'


def url():
    """
    the plugin url name
    :return: string (i.e. 'http://www.lemon64.com')
    """
    return 'http://www.lemon64.com'


def systems():
    """
    the related system/s
    :return: string (i.e. 'Commodore 64')
    """
    return 'c64'


def engine_help():
    """
    help on engine specific '--engine_params' and such
    :return: string
    """
    return 'disk_num=n (set disk number)'
