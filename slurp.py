#!/usr/bin/env python3
"""
Usage: slurp [--hot] [--channel=<channel>] [--user=<user>] [--limit=<limit>]
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
from docopt import docopt
from bs4 import BeautifulSoup

USER_AGENT = 'my awesome reddit app'
DEFAULT_LIMIT = 100
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


def __download_data(url, created, title, ctype):
    """ Download the data from the URL """
    created = datetime.datetime.fromtimestamp(created)
    try:
        ext = KNOWN_CONTENT_TYPES[ctype]
    except KeyError:
        ext = '.dat'
    title = title.strip('.! ')
    target = created.isoformat() + '_' + subst_title(title) + ext
    if os.path.exists(target):
        return '[A]'
    try:
        response = requests.get(url)
        if response:
            clength = 0
            with open(target, 'wb') as fp:
                for chunk in response:
                    clength += fp.write(chunk)
                fp.close()
            return '[D {}]'.format(clength)
        else:
            return '[E {} {}]'.format(url, response.status_code)
    except Exception as error:
        print('{}: {}'.format(type(error), error))


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


def check_link(post):
    """ Check the link for embedded stuff """
    if 'https://imgur.com' in post.url:
        url = post.url.replace('https://', 'https://i.') + '.jpg'
        return __download_data(url, post.created, post.title, 'image/jpeg')
    elif 'https://gfycat.com' in post.url:
        url = find_mp4_link(post.url)
        return __download_data(url, post.created, post.title, 'video/webm')
    else:
        return '[U parse HTML from {}]'.format(post.url)


def process(post):
    """ Process the given submission """
    print(post.title, ': ', end='')
    try:
        response = requests.head(post.url)
    except Exception:
        host = urllib.parse.urlparse(post.url).netloc
        print('[E connection error for {}]'.format(host))
        return
    if not response:
        print('[E {} {}]'.format(post.url, response.status_code))
        return
    if 'Location' in response.headers:
        post.url = urllib.parse.urljoin(post.url, response.headers['location'])
        return process(post)
    if 'Content-Type' not in response.headers:
        print('[E missing content type in {}]'.format(post.url))
        return
    ctype = response.headers['Content-Type']
    content_type = ctype.replace(' ', '').lower()
    if content_type not in KNOWN_CONTENT_TYPES:
        print('[E Unknown content-type {}]'.format(ctype))
        return
    status = 'Unknown Error'
    if 'image' in content_type:
        status = __download_data(post.url, post.created, post.title,
                                 content_type)
    elif 'text' in content_type:
        status = check_link(post)
    else:
        print('[U {}]'.format(ctype))
    print(status)


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


def main():
    args = docopt(__doc__)
    limit = args['--limit'] if args['--limit'] else DEFAULT_LIMIT
    channel = args['--channel'] if args['--channel'] else None
    user = args['--user'] if args['--user'] else None
    configure = args['configure']

    if configure:
        sys.exit(configure_reddit(args))

    try:
        with open(config_path()) as config:
            data = json.loads(''.join(config.readlines()))
            config.close()
    except Exception as error:
        print(error)
        print('Please configure reddit-slurp before using.')
        sys.exit(1)

    if not channel and not user:
        print(__doc__.strip())
        print('Need a channel or reddit user name to slurp media from.')
        sys.exit(0)

    limit = int(limit)
    try:
        reddit = praw.Reddit(
            client_id=data['client-id'],
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

        try:
            os.mkdir(store)
        except FileExistsError:
            pass
        os.chdir(store)

        posts = chan.hot(limit=limit) if args['--hot'] else chan.new(
            limit=limit)
        for post in posts:
            tags = vars(post)
            if 'url' in tags:
                try:
                    process(post)
                except KeyboardInterrupt:
                    sys.exit(1)
        os.chdir(cwd)
    except Exception as error:
        print('{}: {}'.format(type(error), error))
        type_, value_, traceback_ = sys.exc_info()
        traceback.format_tb(traceback_)
        raise
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
