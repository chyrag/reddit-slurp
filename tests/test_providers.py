import providers
from providers import gfycat, imgur, redgifs, redv


def test_imgur_matches():
    assert imgur.matches('https://imgur.com/abc')
    assert not imgur.matches('https://example.com/abc')


def test_gfycat_matches_domain_and_gifv_extension():
    assert gfycat.matches('https://gfycat.com/abc')
    assert gfycat.matches('https://example.com/abc.gifv')
    assert not gfycat.matches('https://example.com/abc')


def test_redgifs_matches():
    assert redgifs.matches('https://www.redgifs.com/watch/abc')
    assert not redgifs.matches('https://redgifs.com/watch/abc')


def test_redv_matches():
    assert redv.matches('https://redv.co/abc')
    assert not redv.matches('https://example.com/abc')


def test_registry_order_matches_original_precedence():
    assert providers.REGISTRY == [imgur, gfycat, redv, redgifs]
