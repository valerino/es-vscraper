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

import requests
from slugify import slugify
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


def _download_ingame_image(soup, args):
    """
    download ingame image
    :param soup: the source soup
    :param args: arguments from cmdline
    :return: string
    """
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

    return img_url


def _download_box_image(soup, args):
    """
    download box image
    :param soup: the source soup
    :param args: arguments from cmdline
    :return: string
    """
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

    return img_url


def _download_title_image(soup, args):
    """
    download box image
    :param soup: the source soup
    :param args: arguments from cmdline
    :return: string
    """
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

    return img_url


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

    if args.img_index == -1:
        try:
            # try to download cover
            img_url = _download_box_image(soup, args)
            got_cover = True
        except Exception as e:
            # fallback to 0
            args.img_index = 0
            pass

    try:
        if not got_cover:
            try:
                if args.img_index == 0:
                    # get ingame
                    img_url = _download_ingame_image(soup, args)
                else:
                    # get title
                    img_url = _download_title_image(soup, args)
            except:
                # fallback to ingame, in case
                img_url = _download_ingame_image(soup, args)

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

    try:
        # name
        container = soup.find('span', id='Out')
        idx = container.contents[0].text.find(' - ')
        game_info['name'] = container.contents[0].text[:idx]
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
    game_info['img_buffer'] = _download_image(soup, args)

    return game_info


def _find_a_text_system(tag):
    if tag.name == 'a' and "'GridView1','System$" in tag['href']:
        return True
    return False


def _find_a_text_game(tag):
    if tag.name == 'a' and "'GridView1','GAME$" in tag['href']:
        return True
    return False


def _find_a_text_publisher(tag):
    if tag.name == 'a' and "'GridView1','PUB$" in tag['href']:
        return True
    return False


def _find_a_text_year(tag):
    if tag.name == 'a' and "'GridView1','YR$" in tag['href']:
        return True
    return False


def _check_response(reply, the_system):
    """
    check server response (not found, single, multi)
    :param reply: the server reply
    :param the_system: the system of interest
    :return: [{name,publisher,year,url,system}] (each except 'name' may be empty)
    """
    html = reply.content
    soup = BeautifulSoup(html, 'html.parser')

    all_systems = soup.find_all(_find_a_text_system)
    games = []
    for g in all_systems:
        slugified_text = slugify(g.text)
        slugified_system = slugify(the_system)
        if slugified_system in slugified_text:
            # found a game entry for the requested system
            p = g.parent.parent.parent
            entry = {}
            entry['name'] = p.find_all(_find_a_text_game)[1].text.replace('\'','')
            entry['publisher'] = p.find(_find_a_text_publisher).text
            entry['year'] = p.find(_find_a_text_year).text
            slugified_gamename = slugify(entry['name'])
            # print('system: %s, game: %s' % (slugified_text, slugified_gamename))
            entry['url'] = 'http://www.gamesdatabase.org/game/%s/%s' % (slugified_text, slugified_gamename)
            entry['system'] = g.text
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
    s = vscraper_utils.get_parameter(args.engine_params, 'system')

    # get game id
    params = {'in': 1, 'searchtext': args.to_search, 'searchtype': 1}
    u = 'http://www.gamesdatabase.org/list.aspx'
    reply = requests.get(u, params=params)

    # check response
    if not reply.ok:
        raise ConnectionError

    choices = _check_response(reply, s)
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
    return 'Multiple (http://www.gamesdatabase.org/systems)'


def engine_help():
    """
    help on engine specific '--engine_params' and such
    :return: string
    """
    return """system=name: specifies target system, substring allowed ("amiga", "spectrum", "coleco", ...)    
        note: img_index=0 (default) downloads in-game screen, img_index=1 downloads title screen (fallback to in-game if not found)"""

