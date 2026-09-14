""" redv.co provider """

import logging

import requests

DEFAULT_TIMEOUT = 10
DOMAIN = 'https://redv.co'


def matches(url):
    """ Whether this provider handles the given post URL """
    return DOMAIN in url


def resolve(url):
    """ Resolve the post URL to a direct media URL """
    logging.debug('redv.co URL')
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
    if response:
        vid = response.text.encode(response.encoding)
        title = url.rstrip('/').split('/')[-1]
        print('FIXME Writing redv page to /tmp/{}; check that for redv link'.
              format(title))
        with open('/tmp/{}'.format(title), 'wb') as data:
            data.write(vid)
    return None
