import sys
import time
import json
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Read portal URL from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    portal_url = config.get('PORTAL_URL')
    if not portal_url:
        print("PORTAL_URL not found in config.json. Please add it.")
        sys.exit(1)

def get_token_from_url(portal_url, max_wait=120, check_interval=5, storage_key="Token"):
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.get(portal_url)

    print(f"Please log in to the portal in the opened browser window ({portal_url})...")

    token = None
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            # 1. Try localStorage
            token_raw = driver.execute_script(f"return window.localStorage.getItem('{storage_key}');")
            if token_raw:
                try:
                    token_json = json.loads(token_raw)
                    token = token_json.get('__raw', token_raw)
                except Exception:
                    token = token_raw
                break

            # 2. Try sessionStorage
            token_raw = driver.execute_script(f"return window.sessionStorage.getItem('{storage_key}');")
            if token_raw:
                try:
                    token_json = json.loads(token_raw)
                    token = token_json.get('__raw', token_raw)
                except Exception:
                    token = token_raw
                break

            # 3. Try cookies
            cookies = driver.get_cookies()
            for cookie in cookies:
                if 'token' in cookie['name'].lower():
                    token = cookie['value']
                    break
            if token:
                break

        except Exception:
            pass

        time.sleep(check_interval)

    driver.quit()

    if token:
        pyperclip.copy(token)
        print("Token found and copied to clipboard!")
        print("Token:", token)
        return token
    else:
        print("Token not found in localStorage, sessionStorage, or cookies after waiting.")
        return None

if __name__ == "__main__":
    get_token_from_url(portal_url)