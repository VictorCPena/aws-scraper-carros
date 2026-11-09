from types import SimpleNamespace

import pytest
from selenium.common.exceptions import TimeoutException

from src import scraper


class Browser:
    current_url = ""
    closed = False

    def get(self, url):
        self.current_url = url

    def find_elements(self, *_):
        if "pag=2" in self.current_url:
            return []
        return [SimpleNamespace(text="synthetic card", is_displayed=lambda: True)]

    def find_element(self, *_):
        return SimpleNamespace(send_keys=lambda _: None)

    def quit(self):
        self.closed = True


def test_capture_reports_empty_page_and_closes_browser(monkeypatch):
    browser = Browser()
    monkeypatch.setattr(scraper, "configurar_driver", lambda: browser)
    monkeypatch.setattr(scraper.time, "sleep", lambda _: None)
    capture = scraper.capturar_paginas(1)
    assert capture == {
        "source": "icarros",
        "cards": [{"page": 1, "text": "synthetic card"}],
    }
    assert browser.closed
    browser.closed = False

    class Wait:
        def __init__(self, driver, timeout):
            self.driver = driver

        def until(self, predicate, message):
            if result := predicate(self.driver):
                return result
            raise TimeoutException(message)

    monkeypatch.setattr(scraper, "WebDriverWait", Wait)
    with pytest.raises(TimeoutException, match="page 2"):
        scraper.capturar_paginas(2)
    assert browser.closed
