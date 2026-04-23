from framework.config.loader import load_config


def test_load_config_with_inline_overrides():
    config = load_config(inline={"concurrency": {"workers": 3}, "targets": [{"url": "http://example.com"}]})
    assert config.concurrency.workers == 3
    assert config.targets[0].url == "http://example.com"
