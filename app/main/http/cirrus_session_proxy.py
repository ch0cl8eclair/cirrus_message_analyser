from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.config.constants import CREDENTIALS, USERNAME, PASSWORD
import time
import sys


def enter_data_into_field(text_file_component, text_to_enter, hit_return=False):
    text_file_component.clear()
    text_file_component.send_keys(text_to_enter)
    if hit_return:
        text_file_component.send_keys(Keys.RETURN)


def login(driver, config):
    username = config.get(CREDENTIALS).get(USERNAME)
    password = config.get(CREDENTIALS).get(PASSWORD)

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


def main():
    config = ConfigSingleton(get_configuration_dict())

    driver = webdriver.Chrome('../../drivers/chromedriver80_win32/chromedriver')
    driver.get("https://cirrusconnect.eu.f4f.com/cirrus-connect/")

    executor_url = driver.command_executor._url
    session_id = driver.session_id
    print("Executor url: {}, session_id: {}".format(executor_url, session_id))


    try:
        user_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "j_username"))
        )
    finally:
        print("Loaded page: {}, logging in...".format(driver.title))
        login(driver, config)

    try:
        user_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "topMenuForm:j_idt17_button"))
        )
    except TimeoutException:
        print("Timeout occured, attempting relogin")
        login(driver, config)
    finally:
        print("Found user dropdown select: {}".format(user_select.text))
        try:
            user_select.click()
        except ElementClickInterceptedException as err:
            print("There is a popup blocking the button press")
            # alert_obj = driver.switch_to.alert
            # alert_obj.accept()
            # div id j_idt10:j_idt11

            alert_div = driver.find_element_by_css_selector('div[id*="j_idt10:j_idt11"]')
            if alert_div:
                # a class ui-dialog-titlebar-icon ui-dialog-titlebar-close ui-corner-all
                alert_close = driver.find_element_by_css_selector('a[class*="ui-dialog-titlebar-icon ui-dialog-titlebar-close ui-corner-all"]')
                alert_close.click()
            else:
                print("Failed to find div popup blocking click")
            driver.find_element_by_id("topMenuForm:j_idt17_button").click()

    print("Attempting to change user")
    dropdown_menu = driver.find_element_by_id("topMenuForm:j_idt17_menu")
    if dropdown_menu:
        super_user_link = dropdown_menu.find_element_by_css_selector('a[class*="ui-menuitem-link ui-corner-all"]')
        print("Found link with text: [{}]".format(super_user_link.text))
        super_user_link_by_text = driver.find_element(By.LINK_TEXT, "Switch to Super")
        print(super_user_link_by_text)
        if super_user_link_by_text:
            super_user_link_by_text.click()
        else:
            print("Failed to find super user link", file=sys.stderr)

        elements = dropdown_menu.find_elements(By.TAG_NAME, 'a')
        for e in elements:
            print("Found anchor {} with text: [{}]".format(e.id, get_children_text(e)))
    else:
        print("Failed to find drop down menu", file=sys.stderr)

    # print("Going to press user dropdown")
    # user_select = driver.find_element_by_id("topMenuForm:j_idt17_button")
    # if user_select:
    #     user_select.click()
    # else:
    #     print("User select item not found")

    # print("Going to press superuser")
    # super_user_menu_item = driver.find_element_by_css_selector('a[class*="ui-menuitem-link ui-corner-all"]')
    # if super_user_menu_item:
    #     super_user_menu_item.click()
    # else:
    #     print("SuperUser select item not found")

    # Wait long
    # click button: topMenuForm:j_idt17_button
    # Wait for popup menu
    # li class = ui-menuitem ui-widget ui-corner-all, role = menuitem
    # a class = ui-menuitem-link ui-corner-all
    print(driver.current_url)
    print("; ".join(["{}={}".format(cookie.get("name"), cookie.get("value")) for cookie in driver.get_cookies()]))
    # print(driver.get_cookies())
    time.sleep(10)
    driver.close()


if __name__ == '__main__':
    main()
