#!/usr/bin/env python3
"""
Usage: slurp [--verbose|--debug] [--hot] [--channel=<channel>] [--user=<user>] [--limit=<limit>]
       slurp configure --client-id=<client_id> --client-secret=<client_secret
"""

import sys
import os
import json
import praw
import requests
import datetime
import traceback
import urllib
import urllib3
import logging
from docopt import docopt
from bs4 import BeautifulSoup

USER_AGENT = 'my awesome reddit app'
DEFAULT_LIMIT = 1000
SUPPORTED_PLATFORMS = ['posix', 'nt']
CONFIG = 'slurp.json'

KNOWN_CONTENT_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'video/webm': '.webm',
    'video/mp4': '.mp4',
    'text/html;charset=utf-8': '.html',
    'text/plain;charset=utf-8': '.txt',
}
VIDEO_PREFERENCES = ['video/webm', 'video/mp4']


def subst_title(title):
    """ Safe substitute for string """
    return title.replace(' ', '_').replace('/', '_')


def _download_media(_post, _ctype):
    """ Download the data from the URL and save it locally """
    created = datetime.datetime.fromtimestamp(_post.created)
    try:
        ext = KNOWN_CONTENT_TYPES[_ctype]
    except KeyError:
        print('Unknown content type: {}'.format(_ctype))
        sys.exit(1)

    title = _post.title.strip('.! ')
    target = '{}_{}_{}{}'.format(created.isoformat(), _post.author,
                                 subst_title(title), ext)
    if os.path.exists(target):
        logging.info('%s [A]', _post.title)
        return True

    clength = 0
    try:
        response = requests.get(_post.url)
        if response:
            with open(target, 'wb') as fp:
                for chunk in response:
                    clength += fp.write(chunk)
                fp.close()
            logging.info('%s [D %d]', _post.title, clength)
            return True
        logging.error('%s [E %d]', _post.url, response.status_code)
    except (requests.ConnectionError, urllib3.exceptions.ProtocolError,
            requests.exceptions.ChunkedEncodingError) as error:
        logging.error('%s [%s]', _post.url, error)
    return False


def find_mp4_link(url):
    """ Find the video link in the webpage pointed to by the url """
    response = requests.get(url)
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        available = {}
        for tag in soup.findAll('main', class_='component-container'):
            for src in tag.findAll('source'):
                available.update({src.get('type'): src.get('src')})
            if available:
                for pref in VIDEO_PREFERENCES:
                    if pref in available:
                        return available[pref]
            return url.replace('https://', 'https://giant.')
        for tag in soup.findAll('meta', property='og:video'):
            return tag['content']
    else:
        print('NO MP4 LINK FOUND in {}'.formta(url))
    return None


def find_redv_link(url):
    response = requests.get(url)
    if response:
        vid = response.text.encode(response.encoding)
        title = url.rstrip('/').split('/')[-1]
        print('FIXME Writing redv page to /tmp/{}; check that for redv link'.
              format(title))
        with open('/tmp/{}'.format(title), 'wb') as data:
            data.write(vid)
            data.close()


def find_media_link(post):
    """ Search the post for known embedded links """
    if 'https://imgur.com' in post.url:
        logging.debug('imgur URL')
        return post.url.replace('https://', 'https://i.') + '.jpg'

    if 'https://gfycat.com' in post.url or post.url.endswith('.gifv'):
        logging.debug('gfycat URL')
        return find_mp4_link(post.url)

    if 'https://redv.co' in post.url:
        logging.debug('redv.co URL')
        return find_redv_link(post.url)

    if 'https://www.redgifs.com' in post.url:
        logging.debug('redgifs URL')
        return find_mp4_link(post.url)

    try:
        return post.media['reddit_video']['fallback_url']
    except (TypeError, KeyError) as error:
        logging.error('No reddit_video link: %s', error)
    return None


def error_handler(post, response):
    """ Error handler """
    logging.error('Status %s %s', response.status_code, post.url)
    return False


def process(post):
    """ Process the given submission """
    # Check URL by requesting HEAD
    try:
        response = requests.head(post.url)
    except requests.ConnectionError as error:
        host = urllib.parse.urlparse(post.url).netloc
        logging.error('[E connection error for %s: %s]', host, error)
        return False

    # Getting HEAD failed
    if not response:
        return error_handler(post, response)

    # Handle redirect
    if 'Location' in response.headers:
        post.url = urllib.parse.urljoin(post.url, response.headers['location'])
        return process(post)

    # If we get text/html, then look for links within the HTML document
    if 'text' in response.headers['Content-Type']:
        post.url = find_media_link(post)
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
        print('{} is not supported.')
        return 1
    config = config_path()
    cdir = os.path.dirname(config)
    if not os.path.exists(cdir):
        try:
            os.mkdir(cdir)
        except OSError as error:
            print(error)
            return 1
    else:
        data = {
            'client-id': args['--client-id'],
            'client-secret': args['--client-secret']
        }
        with open(config, 'w') as fp:
            fp.write(json.dumps(data, indent=4))
            fp.close()
    return 0


def download_posts(_chan, _store, _limit, _hot):
    """ Download post data from the given store """
    try:
        os.mkdir(_store)
    except FileExistsError:
        pass
    os.chdir(_store)

    posts = _chan.hot(limit=_limit) if _hot else _chan.new(limit=_limit)
    for post in posts:
        tags = vars(post)
        if 'url' in tags:
            if not process(post):
                logging.error('Error retrieving %s', post.url)


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
            data = json.loads(''.join(config.readlines()))
            config.close()
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
