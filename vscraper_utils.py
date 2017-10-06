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
from time import sleep
from PIL import Image
import select
import sys
import os
import time
import threading
import urllib.request

if os.name == 'nt':
    import msvcrt

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

def __input_with_timeout_win(prompt, timeout):
    """
    input with timeout, unix version (internal)
    """
    result=''
    class KeyboardThread(threading.Thread):
        def run(self):
            self.timedout = False
            self.input = ''
            while True:
                if msvcrt.kbhit():
                    chr = msvcrt.getche()
                    if ord(chr) == 0x0d:
                        break
                    self.input += str(chr,'utf-8')

                if len(self.input) == 0 and self.timedout:
                    break

    print(prompt)
    it = KeyboardThread()
    it.start()
    it.join(timeout)
    it.timedout = True
    if len(it.input) > 0:
        # wait for rest of input
        it.join()
        result = it.input

    return result


def __input_with_timeout_unix(prompt, timeout):
    """
    input with timeout, unix version (internal)
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [],[], timeout)
    if ready:
        return sys.stdin.readline().rstrip('\n')
    return ''


def input_with_timeout(prompt, timeout = 0):
    """
    show prompt with timeout
    :param prompt: prompt to be shown
    :param timeout: if not 0, timeout to wait for in seconds
    :return: the input as string, may be empty if timeout occurred
    """
    if timeout == 0:
        return input(prompt)
    if os.name == 'nt':
        return __input_with_timeout_win(prompt, timeout)
    return __input_with_timeout_unix(prompt, timeout)


def get_csv_parameter(params, name):
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

def get_text_no_tags(tag, to_strip):
    """
    get text from tag, stripping all given attributes
    :param tag a tag
    :param to_strip attribute to strip
    :return:
    """
    for t in tag.find_all(to_strip):
        t.replaceWith('')
    return tag.text

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

def download_file(url, path, no_overwrite):
    """
    download file from http/s url
    :param url: the complete url i.e. http://path/to/file.zip
    :param path: the destination path
    :param no_overwrite: if true, just exits if the file already exists
    :return: -1 if path exists
    """
    if no_overwrite == True:
        if os.path.exists(path):
            return -1

    try:
        os.remove(path)
    except Exception as e:
        pass
    
    # will except on error
    urllib.request.urlretrieve(url,path)

    # check if the file exists and is sane
    size = os.path.getsize(path)
    if size == 0:
        os.remove(path)
        raise Exception('Download error!')


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

