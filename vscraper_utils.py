"""
es-vscraper utilities

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

import io
from PIL import Image


class MultipleChoicesException(Exception):
    """
    raised when multiple entries are found for a game
    """

    def __init__(self, choices):
        self._choices = choices
        Exception.__init__(self)

    def choices(self):
        """
        the entries
        :return: [{ name, publisher, year, url, system}]
        """
        return self._choices


class GameNotFoundException(Exception):
    """
    raised when a game is not found
    """
    pass

def get_parameter(params, name):
    """
    get parameter from csv string of name=value
    :param params: name=value[,name=value,...]
    :param name: parameter name
    :return: the value
    """
    l = params.split(',')
    for ll in l:
        s = ll.split('=')
        if s[0].lower() == name:
            return s[1]
    return ''


def find_href(root, substring):
    """
    browse all 'a' tags for specific 'href'
    :param root: an html node
    :param substring: a substring (match with startswith()), may be None
    :return: array or None
    """
    tags = root.find_all('a')
    if tags is None:
        return None

    res = []
    for t in tags:
        if t['href'].startswith(substring):
            res.append(t)

    if len(res) == 0:
        return None

    return res


def add_text_from_href(root, substring, coll, key):
    """
    browse all 'a' tags for specific 'href', and set coll[key] as a csv of the 'text' attr of each
    :param root: an html node
    :param substring: a substring (match with startswith())
    :param coll: the collection
    :param key: the key into collection
    :return:
    """
    t = find_href(root, substring)
    if t is None:
        # empty
        coll[key] = ''
        return

    s = ''
    for tt in t:
        s += tt.text + ','
    coll[key] = s[:-1]


def write_to_file(path, buffer):
    """
    write buffer to file
    :param path: path to the file (will be overwritten)
    :param buffer: the buffer
    :return:
    """
    with open(path, 'wb') as f:
        f.write(buffer)


def read_from_file(path):
    """
    read file to buffer
    :param path: path to the file
    :return: buffer
    """
    with open(path, 'rb') as f:
        buffer = f.read()
    return buffer


def img_to_png(buffer):
    """
    convert an image buffer to PNG
    :param buffer: the image
    :return: PNG image buffer or None
    """
    if buffer is None:
        return None
    try:
        img_buffer = io.BytesIO()
        tmp = Image.open(io.BytesIO(buffer))
        tmp.save(img_buffer, 'png')
        if len(img_buffer.getvalue()) > 0:
            return img_buffer.getvalue()
        return None

    except Exception as e:
        return None
