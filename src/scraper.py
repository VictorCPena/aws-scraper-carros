"""Selenium capture and offline replay for used-car listing batches."""

import argparse
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlsplit

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

if __package__:
    from .pipeline import limpar_dados as limpar_dados
    from .pipeline import run_batch
    from .storage import CloudStorage
else:
    from pipeline import limpar_dados as limpar_dados
    from pipeline import run_batch
    from storage import CloudStorage

LOG = logging.getLogger(__name__)
URL = "https://www.icarros.com.br/ache/listaanuncios.jsp?pag={page}&ord=35"
SELECTOR = (By.CLASS_NAME, "card-offer__main-content")
SOURCE_HOSTS = {"icarros.com.br", "www.icarros.com.br"}


def configurar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(30)
    except Exception:
        driver.quit()
        raise
    return driver


def capturar_paginas(paginas: int, *, espera: float = 15, intervalo: float = 3) -> dict:
    if not 1 <= paginas <= 20:
        raise ValueError("Page count must be between 1 and 20")
    if not 2 <= espera <= 60 or not 2 <= intervalo <= 60:
        raise ValueError("Wait and interval must be between 2 and 60 seconds")

    driver = configurar_driver()
    cards = []
    try:
        for page in range(1, paginas + 1):
            if page > 1:
                time.sleep(intervalo)
            driver.get(URL.format(page=page))
            location = urlsplit(driver.current_url)
            if location.scheme != "https" or location.hostname not in SOURCE_HOSTS:
                raise RuntimeError("The source redirected outside the expected host")
            WebDriverWait(driver, espera).until(
                expected_conditions.visibility_of_any_elements_located(SELECTOR),
                message=f"No visible listing cards on page {page}",
            )
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(3):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.5)
            page_cards = [
                {"page": page, "text": card.text} for card in driver.find_elements(*SELECTOR)
            ]
            if not page_cards:
                raise RuntimeError(f"Listing cards disappeared on page {page}")
            cards.extend(page_cards)
            LOG.info("page=%d cards=%d", page, len(page_cards))
    finally:
        driver.quit()
    return {"source": "icarros", "cards": cards}


def executar_scraping(paginas: int = 2) -> dict:
    return run_batch(capturar_paginas(paginas), CloudStorage())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--fixture", type=Path, help="Replay a JSON capture without opening a browser"
    )
    mode.add_argument("--live", action="store_true", help="Capture live pages with Chrome")
    parser.add_argument("--pages", type=int, default=2, help="Live pages to request (1 to 20)")
    parser.add_argument(
        "--output-dir", type=Path, help="Override local output and force LOCAL mode"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    capture = (
        json.loads(args.fixture.read_text(encoding="utf-8"))
        if args.fixture
        else capturar_paginas(args.pages)
    )
    storage = CloudStorage(
        ambiente="LOCAL" if args.output_dir is not None else None,
        local_path=args.output_dir,
    )
    print(json.dumps(run_batch(capture, storage), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
