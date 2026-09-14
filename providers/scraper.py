""" Shared HTML scraping helpers used by more than one site provider """

import requests
from bs4 import BeautifulSoup

DEFAULT_TIMEOUT = 10
VIDEO_PREFERENCES = ['video/webm', 'video/mp4']


def find_mp4_link(url):
    """ Find the video link in the webpage pointed to by the url """
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)
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
        for tag in soup.findAll('source', type_='video/mp4'):
            return tag['src']
    else:
        print('NO MP4 LINK FOUND in {}'.format(url))
    return None
