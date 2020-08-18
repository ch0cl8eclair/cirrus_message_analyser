import logging
import os
import pathlib
import time
from logging.config import fileConfig

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.configuration import get_configuration_dict
from main.config.constants import CREDENTIALS, USERNAME, PASSWORD, CHROME_DRIVER_FOLDER, CIRRUS_CONNECT_WEB_URL, \
    CACHED_COOKIE, CACHE_REF, MIN_30, CIRRUS_CREDENTIALS
from main.utils.utils import error_and_exit

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


DRIVER_ERROR_MSG = "Chrome driver does not exist, please install into drivers directory and set config variable: {}, or set env variable".format(CHROME_DRIVER_FOLDER)


def enter_data_into_field(text_file_component, text_to_enter, hit_return=False):
    text_file_component.clear()
    text_file_component.send_keys(text_to_enter)
    if hit_return:
        text_file_component.send_keys(Keys.RETURN)


def login(driver, config):
    username = config.get(CREDENTIALS).get(CIRRUS_CREDENTIALS).get(USERNAME)
    password = config.get(CREDENTIALS).get(CIRRUS_CREDENTIALS).get(PASSWORD)
    logger.debug("Logging in with username: [{}] and password: [{}]".format(username, password))

    username_field = driver.find_element_by_name("j_username")
    password_field = driver.find_element_by_name("j_password")

    enter_data_into_field(username_field, username)
    enter_data_into_field(password_field, password, True)

    # login_button = driver.find_element_by_id("loginButton")
    # login_button.click()


def get_children_text(tag):
    children = tag.find_elements_by_xpath('*')
    original_text = tag.text
    for child in children:
        original_text = original_text + ", " + child.text
    return original_text


def verify_superuser_dropdown_display(driver, username):
    super_dropdown_menu = driver.find_element_by_id("topMenuForm:j_idt17_button")
    if super_dropdown_menu:
        span_elements = super_dropdown_menu.find_elements(By.TAG_NAME, 'span')
        span_text = ",".join([e.text for e in span_elements])
        if "Super" in span_text and username in span_text:
            logger.info("Successfully switched to superuser")
        else:
            logger.warning("Unable to confirm switch to superuser, some functionality may not work")
    else:
        logger.error("Failed to find dropdown after switch to super user")


def write_cookies_to_file_cache(config, cookies_str):
    config.get(CACHE_REF).set(CACHED_COOKIE, cookies_str, expire=MIN_30)


def read_cookies_file(config):
    return config.get(CACHE_REF)[CACHED_COOKIE]


def cookies_file_exists(config):
    return CACHED_COOKIE in config.get(CACHE_REF)


def chromedriver_file_exists(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file == "chromedriver" or file == "chromedriver.exe":
                return True
    return False


def get_driver_folder_and_validate(configured_chrome_folder):
    p = pathlib.Path(pathlib.Path(__file__).parent, '..', '..', 'drivers')
    logger.debug("Path to driver is: {}, path exists: {}".format(str(p), os.path.exists(str(p))))
    chrome_driver_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'drivers',  configured_chrome_folder)
    if not os.path.exists(chrome_driver_dir):
        logger.error("Failed to find chrome driver within folder: [{}]".format(chrome_driver_dir))
        error_and_exit("Chrome driver folder does not exist")
    logger.info("Chrome driver folder exists: {}".format(os.path.exists(chrome_driver_dir)))
    return chrome_driver_dir


def get_driver_file_and_validate(chrome_driver_dir):
    logger.debug("Checking for chrome driver file located at: {}".format(chrome_driver_dir))
    if not chromedriver_file_exists(chrome_driver_dir):
        logger.error("Failed to find chrome driver within folder: [{}]".format(chrome_driver_dir))
        error_and_exit(DRIVER_ERROR_MSG)
    # Repeating ourselves here but we need to return the full file path to selenium
    chrome_driver_file = os.path.join(chrome_driver_dir, 'chromedriver')
    if not os.path.exists(chrome_driver_dir):
        error_and_exit(DRIVER_ERROR_MSG)
    return chrome_driver_file


def obtain_cookies_from_cirrus_manually():
    # Get config details and check values
    config = ConfigSingleton()
    configured_chrome_folder = config.get(CHROME_DRIVER_FOLDER)
    chrome_driver_dir = get_driver_folder_and_validate(configured_chrome_folder)
    chrome_driver_file = get_driver_file_and_validate(chrome_driver_dir)
    username = config.get(CREDENTIALS).get(CIRRUS_CREDENTIALS).get(USERNAME)

    # Connect driver
    driver = webdriver.Chrome(chrome_driver_file)
    web_url = config.get(CIRRUS_CONNECT_WEB_URL)
    driver.get(web_url)

    # Driver details
    executor_url = driver.command_executor._url
    session_id = driver.session_id
    logger.debug("Executor url: {}, session_id: {}".format(executor_url, session_id))

    # Now perform steps to login and become super user in Cirrus
    # Once done we obtain the cookie and exit the driver
    # We may have an accept cookies popup blocking us so deal with this also.
    try:
        user_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "j_username"))
        )
    finally:
        logger.debug("Loaded page: {}, logging in...".format(driver.title))
        login(driver, config)

    try:
        user_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "topMenuForm:j_idt17_button"))
        )
    except TimeoutException:
        logger.error("Timeout occurred, attempting relogin")
        login(driver, config)
    finally:
        logger.debug("Found user dropdown select: {}".format(user_select.text))
        try:
            user_select.click()
        except ElementClickInterceptedException as err:
            logger.error("There is a popup blocking the button press, attempting to overcome")

            alert_div = driver.find_element_by_css_selector('div[id*="j_idt10:j_idt11"]')
            if alert_div:
                # a class ui-dialog-titlebar-icon ui-dialog-titlebar-close ui-corner-all
                alert_close = driver.find_element_by_css_selector('a[class*="ui-dialog-titlebar-icon ui-dialog-titlebar-close ui-corner-all"]')
                alert_close.click()
            else:
                logger.error("Failed to find div popup blocking click")
            driver.find_element_by_id("topMenuForm:j_idt17_button").click()

    logger.info("Attempting to change user")
    dropdown_menu = driver.find_element_by_id("topMenuForm:j_idt17_menu")
    if dropdown_menu:
        super_user_link = dropdown_menu.find_element_by_css_selector('a[class*="ui-menuitem-link ui-corner-all"]')
        logger.debug("Found link with text: [{}]".format(super_user_link.text))
        super_user_link_by_text = driver.find_element(By.LINK_TEXT, "Switch to Super")
        # logger.debug(super_user_link_by_text)
        if super_user_link_by_text:
            super_user_link_by_text.click()
        else:
            logger.error("Failed to find super user link")
    else:
        logger.error("Failed to find drop down menu")

    logger.debug("Cirrus URL now set to: {}".format(driver.current_url))
    logger.debug("Sleeping for 5 seconds")
    time.sleep(5)
    verify_superuser_dropdown_display(driver, username)

    cirrus_super_user_cookie = "; ".join(["{}={}".format(cookie.get("name"), cookie.get("value")) for cookie in driver.get_cookies()])
    logger.debug("Obtained the Cirrus cookie: {}".format(cirrus_super_user_cookie))
    write_cookies_to_file_cache(config, cirrus_super_user_cookie)
    driver.close()


def main():
    config = ConfigSingleton(get_configuration_dict())
    obtain_cookies_from_cirrus_manually()


if __name__ == '__main__':
    main()
