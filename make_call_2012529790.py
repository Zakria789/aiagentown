"""
CallTools Auto Dialer - Make Call to 2012529790
Automatically logs in and initiates call
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pyautogui

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"

print("╔══════════════════════════════════════════════════════════╗")
print("║  CallTools Auto Dialer - Initiating Call                ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print(f"Target Phone: {PHONE_NUMBER}")
print(f"CallTools URL: {CALLTOOLS_URL}")
print(f"Agent: {USERNAME}")
print()


def wait_and_find(driver, wait, selectors, element_name):
    """Try multiple selectors to find an element"""
    for by, selector in selectors:
        try:
            element = wait.until(EC.presence_of_element_located((by, selector)))
            print(f"✓ Found {element_name}: {selector}")
            return element
        except:
            continue
    return None


def main():
    driver = None
    try:
        # Setup Chrome
        print("[1] Setting up Chrome browser...")
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Allow microphone access
        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.notifications": 1
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        wait = WebDriverWait(driver, 15)
        
        # Navigate to CallTools
        print(f"[2] Opening {CALLTOOLS_URL}...")
        driver.get(CALLTOOLS_URL)
        time.sleep(3)
        
        # Login
        print("[3] Logging in...")
        
        # Username
        username_selectors = [
            (By.ID, "username"),
            (By.ID, "user"),
            (By.NAME, "username"),
            (By.NAME, "user"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.XPATH, "//input[@placeholder='Username' or @placeholder='Email' or @placeholder='User']")
        ]
        
        username_field = wait_and_find(driver, wait, username_selectors, "username field")
        if username_field:
            username_field.clear()
            username_field.send_keys(USERNAME)
            print(f"  Entered username: {USERNAME}")
        else:
            print("✗ Could not find username field!")
            driver.save_screenshot("error_username.png")
            return False
        
        # Password
        password_selectors = [
            (By.ID, "password"),
            (By.ID, "pass"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']")
        ]
        
        password_field = wait_and_find(driver, wait, password_selectors, "password field")
        if password_field:
            password_field.clear()
            password_field.send_keys(PASSWORD)
            print(f"  Entered password")
        else:
            print("✗ Could not find password field!")
            driver.save_screenshot("error_password.png")
            return False
        
        # Login button
        login_selectors = [
            (By.ID, "login"),
            (By.ID, "submit"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'Log In')]")
        ]
        
        login_button = wait_and_find(driver, wait, login_selectors, "login button")
        if login_button:
            login_button.click()
            print("  Clicked login button")
        else:
            print("✗ Could not find login button!")
            driver.save_screenshot("error_login_button.png")
            return False
        
        # Wait for login
        print("[4] Waiting for login to complete...")
        time.sleep(5)
        
        current_url = driver.current_url
        if "login" in current_url.lower():
            print("✗ Login failed - still on login page")
            driver.save_screenshot("login_failed.png")
            return False
        
        print("✓ Login successful!")
        driver.save_screenshot("logged_in.png")
        
        # Look for dialer
        print(f"[5] Looking for dialer interface...")
        time.sleep(3)
        
        # Try to find phone input or manual dial button
        phone_selectors = [
            (By.ID, "phone"),
            (By.ID, "phonenumber"),
            (By.ID, "phone_number"),
            (By.NAME, "phone"),
            (By.NAME, "number"),
            (By.CSS_SELECTOR, "input[type='tel']"),
            (By.XPATH, "//input[@placeholder='Phone Number' or @placeholder='Phone' or @placeholder='Number']"),
            (By.XPATH, "//input[contains(@class, 'phone') or contains(@class, 'number')]")
        ]
        
        phone_field = wait_and_find(driver, wait, phone_selectors, "phone input")
        
        if phone_field:
            # Enter phone number
            phone_field.clear()
            phone_field.send_keys(PHONE_NUMBER)
            print(f"✓ Entered phone number: {PHONE_NUMBER}")
            
            # Look for call/dial button
            call_selectors = [
                (By.ID, "call"),
                (By.ID, "dial"),
                (By.ID, "make_call"),
                (By.XPATH, "//button[contains(text(), 'Call') or contains(text(), 'Dial')]"),
                (By.CSS_SELECTOR, "button.call"),
                (By.CSS_SELECTOR, "button.dial"),
                (By.XPATH, "//button[contains(@class, 'call') or contains(@class, 'dial')]")
            ]
            
            call_button = wait_and_find(driver, wait, call_selectors, "call button")
            if call_button:
                print("[6] Initiating call...")
                call_button.click()
                print(f"✓ Call button clicked!")
                time.sleep(2)
                driver.save_screenshot("call_initiated.png")
            else:
                print("  Trying to press ENTER to dial...")
                phone_field.send_keys(Keys.RETURN)
                time.sleep(2)
                driver.save_screenshot("call_enter.png")
        else:
            print("  No phone input found - looking for manual dial pad...")
            
            # Try to find dial pad or manual dial option
            dialpad_selectors = [
                (By.XPATH, "//button[contains(text(), 'Manual Dial') or contains(text(), 'Make Call')]"),
                (By.ID, "manual_dial"),
                (By.ID, "dialpad"),
                (By.CSS_SELECTOR, ".dialpad"),
                (By.CSS_SELECTOR, ".manual-dial")
            ]
            
            dialpad_button = wait_and_find(driver, wait, dialpad_selectors, "manual dial button")
            if dialpad_button:
                dialpad_button.click()
                print("  Clicked manual dial button")
                time.sleep(2)
                
                # Try phone input again after opening dialpad
                phone_field = wait_and_find(driver, wait, phone_selectors, "phone input after dialpad")
                if phone_field:
                    phone_field.clear()
                    phone_field.send_keys(PHONE_NUMBER)
                    phone_field.send_keys(Keys.RETURN)
                    print(f"✓ Entered number {PHONE_NUMBER} and pressed ENTER")
                    time.sleep(2)
        
        # Check if call is active
        driver.save_screenshot("final_state.png")
        
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  Call Status                                             ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("✓ Browser is open and logged in")
        print("✓ Attempting to dial:", PHONE_NUMBER)
        print()
        print("Screenshots saved:")
        print("  - logged_in.png")
        print("  - final_state.png")
        print()
        print("The browser will stay open for 60 seconds.")
        print("Check if call is connecting...")
        print()
        print("If call initiated, audio will flow:")
        print("  CallTools → VB-Cable → Backend → HumeAI → CallTools")
        print()
        
        # Keep browser open
        for i in range(60, 0, -5):
            print(f"Closing in {i} seconds... (Ctrl+C to keep open)")
            time.sleep(5)
        
        return True
        
    except KeyboardInterrupt:
        print()
        print("Keeping browser open...")
        print("Press Enter when done to close...")
        input()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        if driver:
            driver.save_screenshot("error.png")
            print("Screenshot saved: error.png")
        
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                print("Browser closed.")
            except:
                pass


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
