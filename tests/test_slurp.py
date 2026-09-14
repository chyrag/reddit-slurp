import docopt

import slurp
from providers import gfycat


def test_subst_title():
    assert slurp.subst_title('a b/c') == 'a_b_c'


def test_config_path_uses_home(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('APPDATA', raising=False)
    assert slurp.config_path() == str(tmp_path / '.config' / 'slurp.json')


def test_usage_configure_parses():
    args = docopt.docopt(slurp.__doc__, argv=[
        'configure', '--client-id=abc', '--client-secret=xyz',
    ])
    assert args['--client-id'] == 'abc'
    assert args['--client-secret'] == 'xyz'


def test_configure_reddit_writes_config(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('APPDATA', raising=False)
    args = {'--client-id': 'abc', '--client-secret': 'xyz'}
    assert slurp.configure_reddit(args) == 0

    config = tmp_path / '.config' / 'slurp.json'
    assert config.exists()


class _FakePost:
    def __init__(self, url, media=None):
        self.url = url
        self.media = media


def test_find_media_link_dispatches_to_matching_provider(monkeypatch):
    monkeypatch.setattr(gfycat, 'resolve', lambda url: 'resolved-url')
    post = _FakePost('https://gfycat.com/something')
    assert slurp.find_media_link(post) == 'resolved-url'


def test_find_media_link_falls_back_to_reddit_video():
    post = _FakePost(
        'https://example.com/no-match',
        media={'reddit_video': {'fallback_url': 'https://v.redd.it/abc'}},
    )
    assert slurp.find_media_link(post) == 'https://v.redd.it/abc'
