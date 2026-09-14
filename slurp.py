#!/usr/bin/env python3
"""
Usage: slurp [--verbose|--debug] [--hot] [--channel=<channel>] [--user=<user>] [--limit=<limit>]
       slurp configure --client-id=<client_id> --client-secret=<client_secret>
"""

import sys
import os
import json
import praw
import prawcore
import requests
import datetime
import traceback
import urllib.parse
import urllib3
import logging
from docopt import docopt

import providers

USER_AGENT = 'my awesome reddit app'
DEFAULT_LIMIT = 100
SUPPORTED_PLATFORMS = ['posix', 'nt']
CONFIG = 'slurp.json'
DEFAULT_TIMEOUT = 10
MAX_FILENAME_LENGTH = 250

KNOWN_CONTENT_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'video/webm': '.webm',
    'video/mp4': '.mp4',
    'text/html;charset=utf-8': '.html',
    'text/plain;charset=utf-8': '.txt',
}


def subst_title(title):
    """ Safe substitute for string """
    return title.replace(' ', '_').replace('/', '_')


def _download_media(_post, _ctype):
    """ Download the data from the URL and save it locally """
    created = datetime.datetime.fromtimestamp(_post.created)
    try:
        ext = KNOWN_CONTENT_TYPES[_ctype]
    except KeyError:
        logging.error('Unknown content type: %s', _ctype)
        return False

    title = _post.title.strip('.! ')
    target = '{}_{}_{}{}'.format(created.isoformat(), _post.author,
                                 subst_title(title), ext)

    if len(target) > MAX_FILENAME_LENGTH:
        target = target[:MAX_FILENAME_LENGTH]
    if os.path.exists(target):
        logging.info('%s [A]', _post.title)
        return True

    clength = 0
    try:
        response = requests.get(_post.url, timeout=DEFAULT_TIMEOUT,
                                headers={'User-Agent': USER_AGENT})
        if response:
            with open(target, 'wb') as fp:
                for chunk in response:
                    clength += fp.write(chunk)
            logging.info('%s [D %d]', _post.title, clength)
            return True
        logging.error('%s [E %d]', _post.url, response.status_code)
    except (requests.ConnectionError, urllib3.exceptions.ProtocolError,
            requests.exceptions.ChunkedEncodingError) as error:
        logging.error('%s [%s]', _post.url, error)
    except OSError as error:
        if error.errno == 36:
            logging.error('Filename too long (%d): %s', len(target), target)
    return False


def find_media_link(post):
    """ Search the post for known embedded links """
    for provider in providers.REGISTRY:
        if provider.matches(post.url):
            return provider.resolve(post.url)

    try:
        return post.media['reddit_video']['fallback_url']
    except (TypeError, KeyError) as error:
        logging.error('No reddit_video link: %s', error)
    return None


def error_handler(post, response):
    """ Error handler """
    logging.error('Status %s %s', response.status_code, post.url)
    return False


def save_failed_page(post):
    """ Save an unparseable HTML page locally for debugging """
    failed_dir = '_failed'
    try:
        os.makedirs(failed_dir, exist_ok=True)
        response = requests.get(post.url, timeout=DEFAULT_TIMEOUT,
                                headers={'User-Agent': USER_AGENT})
        target = os.path.join(failed_dir, '{}.html'.format(post.id))
        with open(target, 'wb') as fp:
            fp.write(response.content)
        return target
    except (requests.ConnectionError, requests.exceptions.ReadTimeout,
            OSError) as error:
        logging.error('Failed to save debug page for %s: %s', post.url, error)
        return None


def process(post):
    """ Process the given submission """
    # Check URL by requesting HEAD
    if not post.url:
        logging.debug('Missing URL.')
        return False
    try:
        response = requests.head(post.url, timeout=DEFAULT_TIMEOUT,
                                 headers={'User-Agent': USER_AGENT})
    except (requests.ConnectionError,
            requests.exceptions.MissingSchema,
            requests.exceptions.ReadTimeout) as error:
        logging.error('%s: %s', type(error).__name__, post.url)
        return False

    # Getting HEAD failed
    if not response:
        return error_handler(post, response)

    # Handle redirect (doesn't handle cyclic redirects)
    if 'Location' in response.headers:
        _url = urllib.parse.urljoin(post.url, response.headers['location'])
        logging.debug('[%s redirected to %s]', post.url, _url)
        if _url != post.url:
            post.url = _url
            return process(post)

    # If we get text/html, then look for links within the HTML document
    if 'text' in response.headers['Content-Type']:
        _url = find_media_link(post)
        logging.debug('[received %s; sifting through got %s]',
                      response.headers['Content-Type'], _url)
        if _url is None:
            target = save_failed_page(post)
            if target:
                logging.error('Could not find media link for %s; saved page to %s',
                               post.url, target)
            else:
                logging.error('Could not find media link for %s', post.url)
            return False
        if _url != post.url:
            post.url = _url
            return process(post)

    # If we get non-text/html, then download it
    ctype = response.headers['Content-Type']
    if 'video/' in ctype or 'image/' in ctype:
        return _download_media(post, ctype)

    logging.error('Error handling %s', post.url)
    return False


def config_path():
    """ Return path to the reddit-slurp configuration """
    if 'HOME' in os.environ:
        home = os.getenv('HOME')
    elif 'APPDATA' in os.environ:
        home = os.getenv('APPDATA')
    else:
        home = '/'
    return os.path.join(home, '.config', CONFIG)


def configure_reddit(args):
    """ Configure reddit access """
    if os.name not in SUPPORTED_PLATFORMS:
        print('{} is not supported.'.format(os.name))
        return 1
    config = config_path()
    cdir = os.path.dirname(config)
    if not os.path.exists(cdir):
        try:
            os.mkdir(cdir)
        except OSError as error:
            print(error)
            return 1
    data = {
        'client-id': args['--client-id'],
        'client-secret': args['--client-secret']
    }
    with open(config, 'w') as fp:
        fp.write(json.dumps(data, indent=4))
    return 0


def download_posts(_chan, _store, _limit, _hot):
    """ Download post data from the given store """
    try:
        os.mkdir(_store)
    except FileExistsError:
        pass
    os.chdir(_store)

    try:
        posts = _chan.hot(limit=_limit) if _hot else _chan.new(limit=_limit)
        for post in posts:
            tags = vars(post)
            if 'url' in tags:
                if not process(post):
                    logging.error('Error retrieving %s', post.url)
    except prawcore.exceptions.NotFound as error:
        logging.error(error)


def main():
    args = docopt(__doc__)
    limit = args['--limit'] if args['--limit'] else DEFAULT_LIMIT
    channel = args['--channel'] if args['--channel'] else None
    user = args['--user'] if args['--user'] else None
    configure = args['configure']
    log_level = logging.ERROR
    if args['--debug']:
        log_level = logging.DEBUG
    if args['--verbose']:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s %(message)s')

    if configure:
        return configure_reddit(args)

    try:
        with open(config_path()) as config:
            data = json.load(config)
    except OSError:
        print('Please configure reddit-slurp before using.')
        return 1

    try:
        if not channel and not user:
            print(__doc__.strip())
            print('Need a channel or reddit user name to slurp media from.')
            return 0

        limit = int(limit)
        try:
            reddit = praw.Reddit(client_id=data['client-id'],
                                 client_secret=data['client-secret'],
                                 user_agent=USER_AGENT)
            os.umask(0o22)
            cwd = os.getcwd()
            if channel:
                chan = reddit.subreddit(channel)
                store = channel
            elif user:
                chan = reddit.redditor(user).submissions
                store = user
            download_posts(chan, store, limit, args['--hot'])
            os.chdir(cwd)
        except Exception as error:
            print('{}: {}'.format(type(error), error))
            _, _, traceback_ = sys.exc_info()
            traceback.format_tb(traceback_)
            raise
        return 0
    except KeyboardInterrupt:
        pass
