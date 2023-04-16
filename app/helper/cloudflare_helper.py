import time

from func_timeout import func_timeout, FunctionTimedOut
from pyquery import PyQuery
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import log

ACCESS_DENIED_TITLES = [
    # Cloudflare
    'Access denied',
    # Cloudflare http://bitturk.net/ Firefox
    'Attention Required! | Cloudflare'
]
ACCESS_DENIED_SELECTORS = [
    # Cloudflare
    'div.cf-error-title span.cf-code-label span',
    # Cloudflare http://bitturk.net/ Firefox
    '#cf-error-details div.cf-error-overview h1'
]
CHALLENGE_TITLES = [
    # Cloudflare
    'Just a moment...',
    # DDoS-GUARD
    'DDOS-GUARD',
]
CHALLENGE_SELECTORS = [
    # Cloudflare
    '#cf-challenge-running', '.ray_id', '.attack-box', '#cf-please-wait', '#challenge-spinner', '#trk_jschal_js',
    # Custom CloudFlare for EbookParadijs, Film-Paleis, MuziekFabriek and Puur-Hollands
    'td.info #js_info'
]
SHORT_TIMEOUT = 6


def resolve_challenge(driver: WebDriver, timeout=30):
    try:
        func_timeout(timeout, _evil_logic, args=(driver,))
        return True
    except FunctionTimedOut:
        log.error(f'Error solving the challenge. Timeout after {timeout} seconds.')
        return False
    except Exception as e:
        log.error('Error solving the challenge. ' + str(e))
        return False


def under_challenge(html_text: str):
    """
    Check if the page is under challenge
    :param html_text:
    :return:
    """
    # get the page title
    if not html_text:
        return False
    page_title = PyQuery(html_text)('title').text()
    for title in CHALLENGE_TITLES:
        if page_title == title:
            return True
    for selector in CHALLENGE_SELECTORS:
        html_doc = PyQuery(html_text)
        if html_doc(selector):
            return True
    return False


def _until_title_changes(driver: WebDriver, titles):
    WebDriverWait(driver, SHORT_TIMEOUT).until_not(lambda x: _any_match_titles(x, titles))


def _any_match_titles(driver: WebDriver, titles):
    page_title = driver.title
    for title in titles:
        if page_title == title:
            return True
    return False


def _until_selectors_disappear(driver: WebDriver, selectors):
    WebDriverWait(driver, SHORT_TIMEOUT).until_not(lambda x: _any_match_selectors(x, selectors))


def _any_match_selectors(driver: WebDriver, selectors):
    for selector in selectors:
        html_doc = PyQuery(driver.page_source)
        if html_doc(selector):
            return True
    return False


def _evil_logic(driver: WebDriver):
    driver.implicitly_wait(SHORT_TIMEOUT)
    # wait for the page
    html_element = driver.find_element(By.TAG_NAME, "html")

    # find access denied titles
    if _any_match_titles(driver, ACCESS_DENIED_TITLES):
        raise Exception('Cloudflare has blocked this request. '
                        'Probably your IP is banned for this site, check in your web browser.')
    # find access denied selectors
    if _any_match_selectors(driver, ACCESS_DENIED_SELECTORS):
        raise Exception('Cloudflare has blocked this request. '
                        'Probably your IP is banned for this site, check in your web browser.')

    # find challenge by title
    challenge_found = False
    if _any_match_titles(driver, CHALLENGE_TITLES):
        challenge_found = True
        log.info("Challenge detected. Title found")
    if not challenge_found:
        # find challenge by selectors
        if _any_match_selectors(driver, CHALLENGE_SELECTORS):
            challenge_found = True
            log.info("Challenge detected. Selector found")

    attempt = 0
    if challenge_found:
        while True:
            try:
                attempt = attempt + 1
                # wait until the title changes
                _until_title_changes(driver, CHALLENGE_TITLES)

                # then wait until all the selectors disappear
                _until_selectors_disappear(driver, CHALLENGE_SELECTORS)

                # all elements not found
                break

            except TimeoutException:
                log.debug("Timeout waiting for selector")

                click_verify(driver)

                # update the html (cloudflare reloads the page every 5 s)
                html_element = driver.find_element(By.TAG_NAME, "html")

            # waits until cloudflare redirection ends
        log.debug("Waiting for redirect")
        # noinspection PyBroadException
        try:
            WebDriverWait(driver, SHORT_TIMEOUT).until(EC.staleness_of(html_element))
        except Exception:
            log.debug("Timeout waiting for redirect")

        log.info("Challenge solved!")


def click_verify(driver: WebDriver):
    try:
        log.debug("Try to find the Cloudflare verify checkbox")
        iframe = driver.find_element(By.XPATH, "//iframe[@title='Widget containing a Cloudflare security challenge']")
        driver.switch_to.frame(iframe)
        checkbox = driver.find_element(
            by=By.XPATH,
            value='//*[@id="cf-stage"]//label[@class="ctp-checkbox-label"]/input',
        )
        if checkbox:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(checkbox, 5, 7)
            actions.click(checkbox)
            actions.perform()
            log.debug("Cloudflare verify checkbox found and clicked")
    except Exception as e:
        log.debug(f"Cloudflare verify checkbox not found on the page: {str(e)}")
        # print(e)
    finally:
        driver.switch_to.default_content()

    try:
        log.debug("Try to find the Cloudflare 'Verify you are human' button")
        button = driver.find_element(
            by=By.XPATH,
            value="//input[@type='button' and @value='Verify you are human']",
        )
        if button:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(button, 5, 7)
            actions.click(button)
            actions.perform()
            log.debug("The Cloudflare 'Verify you are human' button found and clicked")
    except Exception as e:
        log.debug(f"The Cloudflare 'Verify you are human' button not found on the page：{str(e)}")
        # print(e)

    time.sleep(2)
