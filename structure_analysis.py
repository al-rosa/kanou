import random
import time

import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.events import (AbstractEventListener,
                                               EventFiringWebDriver)
from selenium.webdriver.support.ui import WebDriverWait


class WebDriverListener(AbstractEventListener):
    def before_navigate_to(self, url, driver):
        print(f"Navigating to: {url}")

    def after_navigate_to(self, url, driver):
        print(f"Navigated to: {url}")


def retry_on_stale(max_attempts=3):
    """StaleElementReferenceException が発生した場合にリトライするデコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException:
                    if attempt == max_attempts - 1:
                        raise
                    print(
                        f"Retrying due to stale element (attempt {attempt + 1})")
                    time.sleep(1)
            return None
        return wrapper
    return decorator


@retry_on_stale(max_attempts=3)
def get_suggestion_info(element: WebElement):
    """サジェスト要素から情報を取得"""
    text = element.text
    link = element.find_element(By.TAG_NAME, "a")
    href = link.get_attribute("href")
    return text, href


def search_and_analyze_perfume(search_term: str):
    options = uc.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.page_load_strategy = 'eager'

    ua = UserAgent()
    options.add_argument(f'--user-agent={ua.random}')

    try:
        print("Initializing Undetected Chrome WebDriver...")
        driver = uc.Chrome(options=options)
        event_driver = EventFiringWebDriver(driver, WebDriverListener())
        wait = WebDriverWait(event_driver, 30)

        print(f"Accessing Fragrantica homepage...")
        event_driver.get("https://www.fragrantica.com/")
        time.sleep(3)

        print("Waiting for search box...")
        search_box = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input.super-search.aa-input"))
        )

        print(f"\nTyping search term: {search_term}")
        for char in search_term:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))

        time.sleep(2)  # サジェストの表示を待つ

        print("Waiting for search suggestions...")
        wait.until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "aa-dropdown-menu"))
        )

        # サジェストを再取得
        suggestion_elements = event_driver.find_elements(
            By.CSS_SELECTOR, ".aa-dropdown-menu .aa-suggestion")

        print("\nAvailable suggestions:")
        suggestions_data = []
        for i, element in enumerate(suggestion_elements[:5]):
            try:
                text, href = get_suggestion_info(element)
                print(f"{i + 1}: {text}")
                suggestions_data.append((text, href))
            except Exception as e:
                print(f"Error processing suggestion {i + 1}: {e}")

        # 目的の香水を探す
        target_url = None
        for text, href in suggestions_data:
            if "Jo Malone" in text and "English Pear" in text:
                print(f"\nFound matching suggestion: {text}")
                target_url = href
                break

        if target_url:
            print(f"Navigating to target URL: {target_url}")
            event_driver.get(target_url)
            time.sleep(5)  # ページ読み込みを待機

            print("\nCurrent page:")
            print(f"Title: {event_driver.title}")
            print(f"URL: {event_driver.current_url}")

            # ページソースを保存
            with open('perfume_page.html', 'w', encoding='utf-8') as f:
                f.write(event_driver.page_source)
            print("Successfully saved perfume page content")
        else:
            print("\nNo matching suggestion found")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        print("\nClosing browser...")
        if 'event_driver' in locals():
            event_driver.quit()
        elif 'driver' in locals():
            driver.quit()


if __name__ == "__main__":
    search_and_analyze_perfume("Jo Malone English Pear Freesia")
