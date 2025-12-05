"""
CallTools Manual Dialer with Complete Interface Navigation
Makes call to 2012529790 by navigating the actual CallTools interface
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"

print("╔══════════════════════════════════════════════════════════╗")
print("║  CallTools Complete Dialer - Manual Call Initiation     ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print(f"📞 Target: {PHONE_NUMBER}")
print(f"🌐 CallTools: {CALLTOOLS_URL}")
print(f"👤 Agent: {USERNAME}")
print()


def main():
    driver = None
    try:
        # Setup Chrome
        print("[Step 1] Initializing Chrome browser...")
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Allow microphone/audio
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
        wait = WebDriverWait(driver, 20)
        
        # Navigate
        print(f"[Step 2] Opening CallTools login page...")
        driver.get(CALLTOOLS_URL)
        time.sleep(5)  # Increased wait for page load
        driver.save_screenshot("step1_homepage.png")
        
        # Login
        print(f"[Step 3] Logging in as {USERNAME}...")
        
        # Find and fill username
        try:
            username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
            time.sleep(1)
            username_field.clear()
            username_field.send_keys(USERNAME)
            print("  ✓ Username entered")
        except Exception as e:
            print(f"  ✗ Username field not found: {e}")
            driver.save_screenshot("error_username.png")
            return False
        
        # Find and fill password
        try:
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(PASSWORD)
            print("  ✓ Password entered")
        except:
            print("  ✗ Password field not found")
            driver.save_screenshot("error_password.png")
            return False
        
        driver.save_screenshot("step2_credentials_entered.png")
        
        # Click login
        try:
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In')]")
            login_button.click()
            print("  ✓ Login button clicked")
        except:
            print("  ✗ Login button not found")
            driver.save_screenshot("error_login.png")
            return False
        
        # Wait for login
        print("[Step 4] Waiting for dashboard to load...")
        time.sleep(6)
        driver.save_screenshot("step3_after_login.png")
        
        # Check if logged in
        if "login" in driver.current_url.lower():
            print("  ✗ Still on login page")
            return False
        
        print("  ✓ Login successful! Dashboard loaded")
        
        # Step 5: Join Campaign
        print("[Step 5] Looking for 'Join Campaign' button...")
        time.sleep(3)
        
        join_campaign_found = False
        join_selectors = [
            "//button[contains(text(), 'Join Campaign')]",
            "//button[contains(text(), 'Join')]",
            "//a[contains(text(), 'Join Campaign')]",
            "//a[contains(text(), 'Join')]",
            "//*[contains(@id, 'join')]",
            "//*[contains(@class, 'join-campaign')]",
        ]
        
        for selector in join_selectors:
            try:
                join_button = driver.find_element(By.XPATH, selector)
                print(f"  ✓ Found 'Join Campaign' button: {join_button.text}")
                join_button.click()
                print(f"  ✓ Clicked 'Join Campaign'")
                join_campaign_found = True
                time.sleep(3)
                driver.save_screenshot("step4_joined_campaign.png")
                break
            except:
                continue
        
        if not join_campaign_found:
            print("  ⚠ 'Join Campaign' button not found - may already be joined")
            driver.save_screenshot("step4_no_join_button.png")
        
        # Step 6: Change Status to Available
        print("[Step 6] Changing status to 'Available'...")
        time.sleep(2)
        
        status_changed = False
        status_selectors = [
            "//select[contains(@id, 'status')]",
            "//select[contains(@name, 'status')]",
            "//button[contains(text(), 'Available')]",
            "//a[contains(text(), 'Available')]",
            "//*[contains(@id, 'available')]",
            "//*[contains(@class, 'status')]",
        ]
        
        for selector in status_selectors:
            try:
                status_element = driver.find_element(By.XPATH, selector)
                
                # Check if it's a dropdown
                if status_element.tag_name == 'select':
                    from selenium.webdriver.support.ui import Select
                    select = Select(status_element)
                    select.select_by_visible_text('Available')
                    print("  ✓ Selected 'Available' from dropdown")
                    status_changed = True
                else:
                    # It's a button or link
                    print(f"  ✓ Found status control: {status_element.text}")
                    status_element.click()
                    print("  ✓ Clicked to set status 'Available'")
                    status_changed = True
                
                time.sleep(2)
                driver.save_screenshot("step5_status_available.png")
                break
            except:
                continue
        
        if not status_changed:
            print("  ⚠ Could not change status - trying to continue anyway")
            driver.save_screenshot("step5_status_not_found.png")
        
        # Step 7: Look for phone number input and manual dial
        print("[Step 7] Looking for manual dial / phone input...")
        time.sleep(2)
        
        phone_input_found = False
        phone_field = None
        
        # Try various selectors for phone input
        phone_selectors = [
            (By.ID, "phone"),
            (By.ID, "phonenumber"),
            (By.ID, "phone_number"),
            (By.ID, "manual_phone"),
            (By.NAME, "phone"),
            (By.NAME, "phonenumber"),
            (By.CSS_SELECTOR, "input[type='tel']"),
            (By.XPATH, "//input[@placeholder='Phone Number']"),
            (By.XPATH, "//input[@placeholder='Phone']"),
            (By.XPATH, "//input[@placeholder='Enter Phone Number']"),
            (By.XPATH, "//input[contains(@class, 'phone')]"),
            (By.XPATH, "//input[contains(@id, 'phone')]"),
            (By.XPATH, "//input[contains(@name, 'phone')]"),
        ]
        
        for by, selector in phone_selectors:
            try:
                phone_field = driver.find_element(by, selector)
                print(f"  ✓ Found phone input field")
                phone_input_found = True
                break
            except:
                continue
        
        if phone_input_found and phone_field:
            # Step 8: Enter phone number
            print(f"[Step 8] Entering phone number: {PHONE_NUMBER}...")
            phone_field.clear()
            time.sleep(0.5)
            phone_field.send_keys(PHONE_NUMBER)
            print(f"  ✓ Phone number entered: {PHONE_NUMBER}")
            time.sleep(1)
            driver.save_screenshot("step6_phone_entered.png")
            
            # Step 9: Click Call/Dial button
            print("[Step 9] Looking for 'Call' or 'Dial' button to start call...")
            time.sleep(1)
            
            call_button_selectors = [
                "//button[contains(text(), 'Call')]",
                "//button[contains(text(), 'Dial')]",
                "//button[contains(text(), 'Start Call')]",
                "//button[contains(text(), 'Make Call')]",
                "//input[@type='submit' and contains(@value, 'Call')]",
                "//input[@type='button' and contains(@value, 'Call')]",
                "//*[@id='call_button']",
                "//*[@id='dial_button']",
                "//*[contains(@class, 'call-button')]",
                "//*[contains(@class, 'dial-button')]",
                "//*[contains(@class, 'btn-call')]",
            ]
            
            call_button_clicked = False
            for selector in call_button_selectors:
                try:
                    call_button = driver.find_element(By.XPATH, selector)
                    print(f"  ✓ Found call button: '{call_button.text}'")
                    call_button.click()
                    print(f"  ✓✓ CALL BUTTON CLICKED! Call initiating to {PHONE_NUMBER}")
                    call_button_clicked = True
                    time.sleep(3)
                    driver.save_screenshot("step7_call_started.png")
                    break
                except:
                    continue
            
            if not call_button_clicked:
                # Try pressing ENTER as fallback
                print("  ⚠ Call button not found, trying ENTER key...")
                phone_field.send_keys(Keys.RETURN)
                time.sleep(2)
                driver.save_screenshot("step7_enter_pressed.png")
        
        else:
            print("  ⚠ No phone input field found")
            print("  Looking for all clickable elements with 'call' or 'dial'...")
            
            # Find all elements with "call" or "dial"
            all_elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'call') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dial')]")
            
            if all_elements:
                print(f"  Found {len(all_elements)} elements with 'call' or 'dial':")
                for elem in all_elements[:5]:  # Show first 5
                    try:
                        print(f"    - {elem.tag_name}: {elem.text[:50]}")
                    except:
                        pass
        
        # Final screenshot
        driver.save_screenshot("step8_final_state.png")
        
        # Summary
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  Call Initiation Summary                                ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("✓ Step 1: Logged in to CallTools")
        print(f"{'✓' if join_campaign_found else '⚠'} Step 2: Joined Campaign")
        print(f"{'✓' if status_changed else '⚠'} Step 3: Status set to Available")
        print(f"{'✓' if phone_input_found else '⚠'} Step 4: Phone number entered ({PHONE_NUMBER})")
        print(f"{'✓' if 'call_button_clicked' in locals() and call_button_clicked else '⚠'} Step 5: Call button clicked")
        print()
        print("📸 Screenshots saved:")
        print("  - step1_homepage.png")
        print("  - step2_credentials_entered.png")
        print("  - step3_after_login.png")
        print("  - step4_joined_campaign.png")
        print("  - step5_status_available.png")
        print("  - step6_phone_entered.png")
        print("  - step7_call_started.png")
        print("  - step8_final_state.png")
        print()
        
        if phone_input_found:
            print("✅ Call should be initiating!")
            print()
            print("🎙️ Audio Flow:")
            print("  Customer speaks → CallTools → VB-Cable")
            print("  VB-Cable → Backend → HumeAI")
            print("  HumeAI → Backend → VB-Cable → CallTools → Customer")
            print()
            print("Make sure audio_bridge_service.py is running!")
        else:
            print("⚠️ Could not automatically dial")
            print("Please check screenshots to manually click dial button")
        
        print()
        print("Browser will stay open for 2 minutes...")
        print("(Press Ctrl+C to keep it open longer)")
        print()
        
        # Keep browser open
        for i in range(120, 0, -10):
            print(f"⏱️  {i} seconds remaining...", end='\r')
            time.sleep(10)
        
        return True
        
    except KeyboardInterrupt:
        print()
        print()
        print("🛑 Interrupted - keeping browser open")
        print("Press Enter when done...")
        input()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        if driver:
            driver.save_screenshot("error_final.png")
        
        return False
        
    finally:
        if driver:
            try:
                print()
                print("Closing browser...")
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
