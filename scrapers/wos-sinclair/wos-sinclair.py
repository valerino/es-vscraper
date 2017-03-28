"""
es-vscraper module for http://www.worldofspectrum.org

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


def _download_image(soup, args):
    """
    download game image
    :param soup: the source soup
    :param args: arguments from cmdline
    :return: image buffer, or None
    """
    got_cover = False
    img_url = ''
    base = 'ihttp://www.worldofspectrum.org'

    if args.img_index == -1:
        # try to get boxart
        try:
            if not args.img_thumbnail:
                # prefer full size, get cover url
                href = soup.find('a', target='_new')['href']
                img_url = urllib.parse.urljoin(base, href)
            else:
                # thumbnail
                img_url = urllib.parse.urljoin(base, soup.find('img', title='Cassette inlay')['src'])
            got_cover = True
        except Exception as e:
            # fallback to 0
            args.img_index = 0
            pass

    try:
        if not got_cover:
            # get screenshot url, 0=ingame, 1=title
            try:
                if args.img_index == 0:
                    img_url = urllib.parse.urljoin(base, soup.find('img', title='In-game screen')['src'])
                else:
                    img_url = urllib.parse.urljoin(base, soup.find('img', title='Loading screen')['src'])
            except:
                # fallback to the one existing, if any
                if args.img_index == 0:
                    img_url = urllib.parse.urljoin(base, soup.find('img', title='Loading screen')['src'])
                else:
                    img_url = urllib.parse.urljoin(base, soup.find('img', title='In-game screen')['src'])
 
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
    game_info['name'] = soup.find('a', title = 'Get direct link to this entry').text

    # publisher
    game_info['publisher'] = soup.find('a', title = 'Find other titles from this publisher').text

    # releasedate
    game_info['releasedate'] = soup.find('font',text='Year of release').findNext('font').text

    # developer
    devs = soup.find_all('a', title='Find other titles by this author')
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
        game_info['developer'] = '-'

    # genre
    game_info['genre'] = soup.find('font',text='Type').findNext('font').text

    # description
    game_info['desc'] = '-'

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
    games_table = soup.find('table', border=0, cellspacing=5)
    if games_table is None:
        # not found
        raise vscraper_utils.GameNotFoundException
    
    # get all results
    rows = games_table.find_all('tr')
    choices = []
    for idx, r in enumerate(rows):
        if idx == 0:
            # skip first (header)
            continue;
        
        entry = {}
        cols = r.find_all('td')
        
        # first column is name
        entry['name'] = vscraper_utils.find_href(cols[0],'/infoseek.cgi?')[0].text.encode('ascii','ignore').decode('utf-8')
        entry['url'] = 'http://www.worldofspectrum.org%s' % vscraper_utils.find_href(cols[0],'/infoseek.cgi?')[0]['href']
        
        # year is 2nd
        entry['year']=cols[1].find('font').text
        
        # publisher is 3rd
        entry['publisher']=cols[2].find('font').text
        
        # done
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
    params = {'what': '1', 'regexp': args.to_search, 'loadpics': 3, 'yrorder': '1','scorder':'1','have':'1','also':'1','sort':'1','display':'1'}
    u = 'http://www.worldofspectrum.org/infoseekadv.cgi'
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
    return 'wos-sinclair'


def url():
    """
    the plugin url name
    :return: string (i.e. 'http://www.lemon64.com')
    """
    return 'http://www.worldofspectrum.org'


def systems():
    """
    the related system/s
    :return: string (i.e. 'Commodore 64')
    """
    return 'Sinclair ZX Spectrum/ZX-81'


def engine_help():
    """
    help on engine specific '--engine_params' and such
    :return: string
    """
    return 'note: img_index=0 (default) downloads in-game screen, img_index=1 downloads title screen (fallback to in-game if not found)'
