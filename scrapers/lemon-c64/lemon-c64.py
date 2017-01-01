"""
es-vscraper module for http://www.lemon64.com

"""
import re

import requests
from bs4 import BeautifulSoup
import vscraper_utils


def _download_image(soup, img_index=0, img_cover=False):
    """
    download game image
    :param soup: the source soup
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
                r = re.search('(.+=)([0-9]+)', soup.find('link', rel='canonical').attrs['href'])
                gameid = r.group(2)
                u = 'http://www.lemon64.com/games/view_cover.php?gameID=%s' % gameid
                reply = requests.get(u)
                html = reply.content
                s = BeautifulSoup(html, 'html.parser')
                img_url = s.find('img').attrs['src']
                got_cover = True
            except:
                pass

        if not got_cover:
            # get screenshot url
            img_urls = soup.find_all('img', 'pic')
            selected_img = img_urls[img_index]
            img_url = selected_img.attrs['src']

        # download
        reply = requests.get(img_url)
        img = reply.content

        # convert to png
        img_buffer = vscraper_utils.img_to_png(img)
        return img_buffer
    except:
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
        soup = BeautifulSoup(html, 'html.parser')
        descr = soup.find('td', 'tablecolor').text.strip()
        descr = descr[:descr.rfind('Downloads:')]
        return descr
    except:
        # no review
        return ''


def run_direct_url(u, img_index=0, img_cover=False):
    """
    perform query with the given direct url
    :param u: the game url
    :param img_index: 0-based index of the image to download, default 0
    :param img_cover: True to download boxart cover as image, default False. If boxart is not available, the first image found is used
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

    # name
    container = soup.find('td', class_='normalheadblank')
    game_info['name'] = container.contents[1].text.strip()

    # publisher
    vscraper_utils.add_text_from_href(soup, 'list.php?publisher', game_info, 'publisher')

    # releasedate
    vscraper_utils.add_text_from_href(soup, 'list.php?year', game_info, 'releasedate')

    # developer
    vscraper_utils.add_text_from_href(soup, 'list.php?coder', game_info, 'developer')

    # genre
    vscraper_utils.add_text_from_href(soup, 'list.php?genre', game_info, 'genre')

    # image
    game_info['img_buffer'] = _download_image(soup, img_index, img_cover)

    # description
    game_info['desc'] = _download_descr(soup)

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
            entry['name']= vscraper_utils.find_href(g, 'details.php')[0].text
            entry['url'] = 'http://www.lemon64.com/games/%s' % (vscraper_utils.find_href(g, 'details.php')[0]['href'])
            vscraper_utils.add_text_from_href(g, '?year', entry, 'year')
            vscraper_utils.add_text_from_href(g, '?publisher', entry, 'publisher')
            choices.append(entry)
        return choices

    # single entry
    choices.append({"url": reply.url})
    return choices


def run(to_search, img_index=0, img_cover=False):
    """
    perform query with the given game title
    :param to_search: the game title
    :param img_index: 0-based index of the image to download, default 0
    :param img_cover: True to download boxart cover as image, default False. If boxart is not available, the first image found is used
    :return: dictionary { name, publisher, developer, genre, releasedate, desc, png_img_buffer } (each may be empty)
    """
    # get game id
    params = {'type': 'title', 'name': to_search}
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
    return run_direct_url(choices[0]['url'], img_index, img_cover)


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


def system():
    """
    the related system (descriptive)
    :return: string (i.e. 'Commodore 64')
    """
    return 'Commodore 64'


def system_short():
    """
    the related system (short)
    :return: string (i.e. 'c64')
    """
    return 'c64'
