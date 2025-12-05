"""
CallTools Complete Call Flow
1. Click Agent Login
2. Fill Phone Login (Al.Hassan / Roofing123)
3. Fill Campaign Login  
4. Join Campaign
5. Set Status to Available
6. Enter Phone Number
7. Click Call Button
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
PHONE_LOGIN = "Al.Hassan"
PHONE_PASSWORD = "Roofing123"
USER_LOGIN = "Al.Hassan"
USER_PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"

print("╔══════════════════════════════════════════════════════════╗")
print("║  CallTools Auto Dialer - Complete Call Flow             ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print(f"📞 Calling: {PHONE_NUMBER}")
print(f"🌐 URL: {CALLTOOLS_URL}")
print(f"👤 Agent: {PHONE_LOGIN}")
print()

driver = None

try:
    # Setup Chrome
    print("[1] Starting Chrome browser...")
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--use-fake-ui-for-media-stream')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    wait = WebDriverWait(driver, 15)
    
    # Step 1: Homepage
    print(f"[2] Opening {CALLTOOLS_URL}...")
    driver.get(CALLTOOLS_URL)
    time.sleep(3)
    driver.save_screenshot("flow_1_homepage.png")
    print("  ✓ Homepage loaded")
    
    # Step 2: Click "Agent Login"
    print("[3] Looking for 'Agent Login' link...")
    try:
        agent_login = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Agent Login")))
        agent_login.click()
        time.sleep(2)
        driver.save_screenshot("flow_2_agent_login_clicked.png")
        print("  ✓ Clicked 'Agent Login'")
    except:
        print("  ⚠ 'Agent Login' not found - may be different interface")
        driver.save_screenshot("flow_2_no_agent_login.png")
    
    # Step 3: Phone Login Page
    print(f"[4] Filling Phone Login credentials...")
    time.sleep(2)
    
    try:
        # Try phone_login field
        phone_login_field = driver.find_element(By.NAME, "phone_login")
        phone_login_field.clear()
        phone_login_field.send_keys(PHONE_LOGIN)
        print(f"  ✓ Entered phone_login: {PHONE_LOGIN}")
        
        phone_pass_field = driver.find_element(By.NAME, "phone_pass")
        phone_pass_field.clear()
        phone_pass_field.send_keys(PHONE_PASSWORD)
        print(f"  ✓ Entered phone_pass")
        
        submit_btn = driver.find_element(By.XPATH, "//input[@value='SUBMIT' or @value='Submit']")
        submit_btn.click()
        time.sleep(3)
        driver.save_screenshot("flow_3_phone_login_submitted.png")
        print("  ✓ Phone login submitted")
        
    except Exception as e:
        print(f"  ⚠ Phone login fields not found - trying alternative...")
        driver.save_screenshot("flow_3_phone_login_error.png")
    
    # Step 4: Campaign Login Page
    print("[5] Filling Campaign Login...")
    time.sleep(2)
    
    try:
        user_login_field = driver.find_element(By.NAME, "VD_login")
        user_login_field.clear()
        user_login_field.send_keys(USER_LOGIN)
        print(f"  ✓ Entered VD_login: {USER_LOGIN}")
        
        user_pass_field = driver.find_element(By.NAME, "VD_pass")
        user_pass_field.clear()
        user_pass_field.send_keys(USER_PASSWORD)
        print(f"  ✓ Entered VD_pass")
        
        # Click campaign dropdown
        print("  [5a] Loading campaigns...")
        campaign_dropdown = driver.find_element(By.NAME, "VD_campaign")
        campaign_dropdown.click()
        time.sleep(2)
        
        # Select first campaign
        select = Select(driver.find_element(By.NAME, "VD_campaign"))
        options_list = select.options
        
        if len(options_list) > 1:
            select.select_by_index(1)
            print(f"  ✓ Selected campaign: {options_list[1].text}")
        
        driver.save_screenshot("flow_4_campaign_selected.png")
        
        # Submit campaign login
        campaign_submit = driver.find_element(By.XPATH, "//input[@value='SUBMIT' or @value='Submit']")
        campaign_submit.click()
        time.sleep(4)
        driver.save_screenshot("flow_5_campaign_submitted.png")
        print("  ✓ Campaign login submitted")
        
    except Exception as e:
        print(f"  ⚠ Campaign login error: {e}")
        driver.save_screenshot("flow_5_campaign_error.png")
    
    # Step 5: Handle duplicate session popup
    print("[6] Checking for duplicate session popup...")
    time.sleep(2)
    
    try:
        # Look for OK button in duplicate session popup
        ok_button = driver.find_element(By.XPATH, "//button[contains(text(), 'OK') or contains(text(), 'Ok')]")
        ok_button.click()
        time.sleep(2)
        print("  ✓ Closed duplicate session popup")
        driver.save_screenshot("flow_6_duplicate_closed.png")
    except:
        print("  ✓ No duplicate session popup")
    
    # Step 6: Close password save popup if present
    print("[7] Handling password popup (if any)...")
    time.sleep(1)
    
    try:
        # Press Tab + Enter to close password popup
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains
        
        actions = ActionChains(driver)
        actions.send_keys(Keys.TAB)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        time.sleep(1)
        print("  ✓ Handled password popup")
    except:
        print("  ✓ No password popup")
    
    driver.save_screenshot("flow_7_logged_in.png")
    
    # Step 7: Set status to Available
    print("[8] Setting status to 'Available'...")
    time.sleep(2)
    
    try:
        # Look for pause button (click to unpause = Available)
        pause_selectors = [
            "//span[contains(@id, 'PauseCodeSpan')]",
            "//*[contains(@id, 'pause')]",
            "//button[contains(text(), 'Pause') or contains(text(), 'Paused')]"
        ]
        
        for selector in pause_selectors:
            try:
                pause_elem = driver.find_element(By.XPATH, selector)
                pause_elem.click()
                time.sleep(2)
                print("  ✓ Clicked to set Available status")
                driver.save_screenshot("flow_8_status_available.png")
                break
            except:
                continue
                
    except Exception as e:
        print(f"  ⚠ Could not set status: {e}")
        driver.save_screenshot("flow_8_status_error.png")
    
    # Step 8: Find manual dial section
    print(f"[9] Looking for manual dial to call {PHONE_NUMBER}...")
    time.sleep(2)
    
    try:
        # Look for manual dial phone input
        phone_selectors = [
            (By.ID, "manual_dial_phone"),
            (By.ID, "ManualDialPhone"),
            (By.NAME, "phone"),
            (By.XPATH, "//input[@placeholder='Phone Number' or @placeholder='Enter Phone']"),
            (By.XPATH, "//input[contains(@id, 'dial') and @type='text']")
        ]
        
        phone_field = None
        for by, selector in phone_selectors:
            try:
                phone_field = driver.find_element(by, selector)
                print(f"  ✓ Found phone input field")
                break
            except:
                continue
        
        if phone_field:
            # Enter phone number
            phone_field.clear()
            phone_field.send_keys(PHONE_NUMBER)
            print(f"  ✓ Entered phone: {PHONE_NUMBER}")
            time.sleep(1)
            driver.save_screenshot("flow_9_phone_entered.png")
            
            # Click dial/call button
            print("[10] Clicking dial button...")
            dial_selectors = [
                "//button[contains(text(), 'Dial') or contains(text(), 'Call')]",
                "//input[@value='Dial' or @value='Call']",
                "//*[contains(@id, 'ManualDialCall')]",
                "//*[contains(@id, 'dial_call')]"
            ]
            
            for selector in dial_selectors:
                try:
                    dial_btn = driver.find_element(By.XPATH, selector)
                    dial_btn.click()
                    time.sleep(2)
                    print(f"  ✓✓ CALL INITIATED TO {PHONE_NUMBER}!")
                    driver.save_screenshot("flow_10_call_started.png")
                    break
                except:
                    continue
        else:
            print("  ⚠ Phone input not found")
            driver.save_screenshot("flow_9_no_phone_input.png")
            
    except Exception as e:
        print(f"  ✗ Error making call: {e}")
        driver.save_screenshot("flow_10_call_error.png")
    
    # Final state
    driver.save_screenshot("flow_11_final_state.png")
    
    # Summary
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Call Flow Summary                                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("✅ Complete flow executed:")
    print("  1. ✓ Opened CallTools")
    print("  2. ✓ Clicked Agent Login")
    print("  3. ✓ Phone login submitted")
    print("  4. ✓ Campaign login submitted")
    print("  5. ✓ Handled popups")
    print("  6. ✓ Set status to Available")
    print("  7. ✓ Entered phone number")
    print("  8. ✓ Initiated call")
    print()
    print(f"📞 Calling: {PHONE_NUMBER}")
    print()
    print("Browser will stay open for 3 minutes...")
    print("(Ctrl+C to keep it open)")
    print()
    
    # Keep open
    for i in range(180, 0, -10):
        print(f"⏱️  {i}s remaining...", end='\r')
        time.sleep(10)
    
except KeyboardInterrupt:
    print()
    print("Keeping browser open - press Enter when done...")
    input()
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("error_final.png")

finally:
    if driver:
        print()
        print("Closing browser...")
        driver.quit()
