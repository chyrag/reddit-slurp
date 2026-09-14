""" gfycat.com provider """

import logging

from . import scraper

DOMAIN = 'https://gfycat.com'


def matches(url):
    """ Whether this provider handles the given post URL """
    return DOMAIN in url or url.endswith('.gifv')


def resolve(url):
    """ Resolve the post URL to a direct media URL """
    logging.debug('gfycat URL')
    return scraper.find_mp4_link(url)
