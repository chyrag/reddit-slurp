import docopt

import slurp


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
