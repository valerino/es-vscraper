"""
es-vscraper module for http://www.lemonamiga.com

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


def _download_image(soup, u, args):
    """
    download game image
    :param soup: the html
    :param u: the game url
    :param args: arguments from cmdline
    :return: image buffer, or None
    """
    img_url = ''
    got_cover = False

    if args.img_index == -1:
        # try to get boxart
        try:
            covers = vscraper_utils.find_href(soup, 'box.php?id=')
            if not args.img_thumbnail:
                # prefer the full picture
                cover_url = 'http://www.lemonamiga.com/games/%s' % covers[0]['href']
                reply = requests.get(cover_url)
                html = reply.content
                s = BeautifulSoup(html, 'html.parser')
                img_urls = s.find_all('img', {'name': 'box'})
                img_url = 'http://www.lemonamiga.com%s' % img_urls[0]['src']
            else:
                # thumbnail
                img_url = 'http://www.lemonamiga.com%s' % covers[0].find('img')['src']

            got_cover = True
        except Exception as e:
            # fallback to 0
            args.img_index = 0
            pass

    try:
        if not got_cover:
            # get to screens page
            r = re.search('(.+=)([0-9]+)', u)
            gameid = r.group(2)

            reply = requests.get('http://www.lemonamiga.com/games/screens.php?id=%s' % gameid)
            html = reply.content
            s = BeautifulSoup(html, 'html.parser')
            img_urls = s.find_all('img')
            try:
                selected_img = img_urls[args.img_index]
            except:
                # always fallback to 0, if exist
                selected_img = img_urls[0]

            img_url = selected_img.attrs['src']
            if not args.img_thumbnail:
                # prefer the full picture
                img_url = img_url.replace('/small/', '/full/')

        # download
        reply = requests.get(img_url)
        img = reply.content

        # convert to png
        img_buffer = vscraper_utils.img_to_png(img)
        return img_buffer

    except Exception as e:
        return None


def _download_descr(soup, u):
    """
    download description/review
    :param soup: the html
    :param u: the game url
    :return: description/review
    """

    # search for review / description
    try:
        review_url = vscraper_utils.find_href(soup, '/reviews/view.php')[0]['href']
        reply = requests.get('http://www.lemonamiga.com%s' % review_url)

        # got review page
        html = reply.content

        # parse desc
        s = BeautifulSoup(html, 'html.parser')
        descr = s.find_all('td')[22].text.strip()
        return descr
    except:
        # no review, try comments
        try:
            r = re.search('(.+=)([0-9]+)', u)
            gameid = r.group(2)
            reply = requests.get('http://www.lemonamiga.com/games/comments/text.php?game_id=%s' % gameid)
            html = reply.content
            s = BeautifulSoup(html, 'html.parser')
            spans = s.find_all('span')
            sib = spans[0].next_sibling
            descr = sib.contents[0].strip()
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
    container = soup.find('strong', class_='textGameHeader')
    game_info['name'] = container.text

    # publisher
    vscraper_utils.add_text_from_href(soup, 'list.php?list_publisher', game_info, 'publisher')

    # releasedate
    vscraper_utils.add_text_from_href(soup, 'list.php?list_year', game_info, 'releasedate')

    # developer
    devs = soup.find('td', text='Coder:')
    if devs is None:
        game_info['developer'] = ''
    else:
        vscraper_utils.add_text_from_href(devs.next_sibling, 'list.php?list_people', game_info, 'developer')

    # genre
    vscraper_utils.add_text_from_href(soup, 'list.php?list_genre', game_info, 'genre')

    # description
    game_info['desc'] = _download_descr(soup, u)

    # image
    game_info['img_buffer'] = _download_image(soup, u, args)

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

    # check multi choice/ non existent
    games = soup.find_all('td', 'tablecolor')
    if len(games) is 0:
        raise vscraper_utils.GameNotFoundException

    # build a list
    choices = []
    for g in games:
        entry = {}
        entry['name'] = vscraper_utils.find_href(g, 'details.php')[0].text
        entry['url'] = 'http://www.lemonamiga.com/games/%s' % (vscraper_utils.find_href(g, 'details.php')[0]['href'])
        vscraper_utils.add_text_from_href(g, '?list_year', entry, 'year')
        vscraper_utils.add_text_from_href(g, '?list_publisher', entry, 'publisher')
        choices.append(entry)
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
    params = {'list_title': args.to_search}
    u = 'http://www.lemonamiga.com/games/list.php'
    reply = requests.get(u, params=params)

    # check response
    if not reply.ok:
        raise ConnectionError

    choices = _check_response(reply)
    if len(choices) > 1:
        # return to es-vscraper with a multi choice
        raise vscraper_utils.MultipleChoicesException(choices)

    # got response with the database id, reissue
    return run_direct_url(choices[0]['url'], args)


def name():
    """
    the plugin name
    :return: string (i.e. 'lemon64')
    """
    return 'lemon-amiga'


def url():
    """
    the plugin url name
    :return: string (i.e. 'http://www.lemon64.com')
    """
    return 'http://www.lemonamiga.com'


def systems():
    """
    the related system/s
    :return: string (i.e. 'Commodore 64')
    """
    return 'Commodore Amiga'


def engine_help():
    """
    help on engine specific '--engine_params' and such
    :return: string
    """
    return ''
