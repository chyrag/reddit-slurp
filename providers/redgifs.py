""" redgifs.com provider """

import logging

from . import scraper

DOMAIN = 'https://www.redgifs.com'


def matches(url):
    """ Whether this provider handles the given post URL """
    return DOMAIN in url


def resolve(url):
    """ Resolve the post URL to a direct media URL """
    logging.debug('redgifs URL')
    return scraper.find_mp4_link(url)
