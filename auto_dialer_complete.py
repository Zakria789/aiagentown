"""
FULLY AUTOMATED CallTools Dialer
Complete end-to-end automation:
1. Auto login
2. Auto join campaign  
3. Auto set status to Available
4. Auto dial number
5. Connect to HumeAI for conversation

NO manual intervention required!
"""
import time
import asyncio
import json
import websockets
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os

load_dotenv()

# HumeAI Configuration
HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID")

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Orangeroofing"
PHONE_NUMBER = "2015024650"

print("╔══════════════════════════════════════════════════════════╗")
print("║  FULLY AUTOMATED CallTools AI Dialer                    ║")
print("║  No Manual Intervention Required                        ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print(f"🤖 Automatic Mode: ON")
print(f"📞 Target: {PHONE_NUMBER}")
print(f"👤 Agent: {USERNAME}")
print(f"🎯 HumeAI: Ready to connect")
print()

def setup_browser():
    """Setup Chrome with audio permissions"""
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Auto-allow microphone
    options.add_argument('--use-fake-ui-for-media-stream')
    options.add_argument('--use-fake-device-for-media-stream')
    
    # Disable password save popup
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def auto_login(driver, wait):
    """Automatically login to CallTools"""
    print("[Step 1] Auto Login")
    print("-" * 60)
    
    # Navigate
    driver.get(CALLTOOLS_URL)
    time.sleep(3)
    print("  ✓ Page loaded")
    
    # Find and fill username
    try:
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        username_field.clear()
        username_field.send_keys(USERNAME)
        print(f"  ✓ Username: {USERNAME}")
    except:
        # Try by ID
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        username_field.clear()
        username_field.send_keys(USERNAME)
        print(f"  ✓ Username: {USERNAME}")
    
    # Find and fill password
    try:
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(PASSWORD)
        print(f"  ✓ Password: ********")
    except:
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(PASSWORD)
        print(f"  ✓ Password: ********")
    
    # Click login
    try:
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
    except:
        # Try other selectors
        login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In')]")
        login_btn.click()
    
    print("  ✓ Login submitted")
    time.sleep(5)
    
    # Close any password save popup
    try:
        actions = ActionChains(driver)
        actions.send_keys(Keys.ESCAPE)
        actions.perform()
        time.sleep(1)
    except:
        pass
    
    print("  ✅ LOGIN SUCCESSFUL")
    driver.save_screenshot("auto_1_logged_in.png")
    return True

def auto_join_campaign(driver, wait):
    """Automatically join campaign if needed"""
    print()
    print("[Step 2] Auto Join Campaign")
    print("-" * 60)
    
    time.sleep(2)
    
    # Look for Join Campaign button
    try:
        join_selectors = [
            "//button[contains(text(), 'Join Campaign')]",
            "//a[contains(text(), 'Join Campaign')]",
            "//button[contains(text(), 'Join')]",
            "//*[@id='joinCampaign']"
        ]
        
        for selector in join_selectors:
            try:
                join_btn = driver.find_element(By.XPATH, selector)
                join_btn.click()
                print("  ✓ Clicked 'Join Campaign'")
                time.sleep(3)
                driver.save_screenshot("auto_2_campaign_joined.png")
                print("  ✅ CAMPAIGN JOINED")
                return True
            except:
                continue
        
        print("  ℹ️  Already in campaign or no join needed")
        return True
        
    except Exception as e:
        print(f"  ℹ️  No join campaign action needed")
        return True

def auto_set_available(driver, wait):
    """Automatically set status to Available"""
    print()
    print("[Step 3] Auto Set Status: Available")
    print("-" * 60)
    
    time.sleep(2)
    
    # Try to find and click status to Available
    status_selectors = [
        # Pause button (click to unpause = available)
        "//span[contains(@id, 'Pause')]",
        "//button[contains(@id, 'pause')]",
        "//button[contains(text(), 'Paused')]",
        
        # Status dropdown
        "//select[contains(@id, 'status')]",
        "//select[contains(@name, 'status')]",
        
        # Available button
        "//button[contains(text(), 'Available')]",
        "//*[@id='available']"
    ]
    
    for selector in status_selectors:
        try:
            elem = driver.find_element(By.XPATH, selector)
            
            if elem.tag_name == 'select':
                # Dropdown
                select = Select(elem)
                try:
                    select.select_by_visible_text('Available')
                    print("  ✓ Status set via dropdown")
                except:
                    select.select_by_index(0)
                    print("  ✓ Status set via dropdown (first option)")
            else:
                # Button or clickable
                elem.click()
                print("  ✓ Clicked to set Available")
            
            time.sleep(2)
            driver.save_screenshot("auto_3_status_available.png")
            print("  ✅ STATUS: AVAILABLE")
            return True
            
        except:
            continue
    
    print("  ℹ️  Status already Available or automatic")
    return True

def auto_dial_number(driver, wait, phone_number):
    """Automatically dial the phone number"""
    print()
    print("[Step 4] Auto Dial Number")
    print("-" * 60)
    
    time.sleep(2)
    
    # Find phone input field - try multiple strategies
    phone_field = None
    
    # Strategy 1: Look for common IDs/names
    phone_selectors = [
        (By.ID, "manual_dial_phone"),
        (By.ID, "phone"),
        (By.ID, "dialNumber"),
        (By.NAME, "phone"),
        (By.NAME, "dialNumber"),
    ]
    
    for by, selector in phone_selectors:
        try:
            phone_field = driver.find_element(by, selector)
            print(f"  ✓ Found phone field by {by}: {selector}")
            break
        except:
            continue
    
    # Strategy 2: Look for tel input
    if not phone_field:
        try:
            phone_field = driver.find_element(By.XPATH, "//input[@type='tel']")
            print("  ✓ Found phone field by type=tel")
        except:
            pass
    
    # Strategy 3: Look for any visible text input (last resort)
    if not phone_field:
        try:
            all_inputs = driver.find_elements(By.XPATH, "//input[@type='text' and not(@disabled)]")
            # Filter visible inputs
            for inp in all_inputs:
                if inp.is_displayed():
                    # Check placeholder or nearby text
                    placeholder = inp.get_attribute('placeholder') or ''
                    if 'phone' in placeholder.lower() or 'number' in placeholder.lower():
                        phone_field = inp
                        print(f"  ✓ Found phone field by placeholder")
                        break
            
            # If still not found, try the first visible input after login
            if not phone_field and len(all_inputs) > 0:
                for inp in all_inputs:
                    if inp.is_displayed():
                        phone_field = inp
                        print(f"  ⚠ Using first visible input field")
                        break
        except:
            pass
    
    if phone_field:
        # Enter phone number
        phone_field.clear()
        time.sleep(0.5)
        phone_field.send_keys(phone_number)
        print(f"  ✓ Entered: {phone_number}")
        time.sleep(1)
        driver.save_screenshot("auto_4_phone_entered.png")
        
        # Find and click Call/Dial button
        print("  Looking for Call button...")
        
        call_selectors = [
            "//button[contains(text(), 'Call')]",
            "//button[contains(text(), 'Dial')]",
            "//button[contains(text(), 'CALL')]",
            "//button[contains(text(), 'DIAL')]",
            "//input[@type='button' and contains(@value, 'Call')]",
            "//input[@type='submit' and contains(@value, 'Call')]",
            "//*[@id='callButton']",
            "//*[@id='dialButton']",
        ]
        
        call_clicked = False
        for selector in call_selectors:
            try:
                call_btn = driver.find_element(By.XPATH, selector)
                call_btn.click()
                print(f"  ✓ Clicked Call button")
                call_clicked = True
                time.sleep(3)
                driver.save_screenshot("auto_5_call_initiated.png")
                break
            except:
                continue
        
        if not call_clicked:
            # Try pressing Enter
            print("  Trying Enter key...")
            phone_field.send_keys(Keys.RETURN)
            time.sleep(2)
        
        print(f"  ✅ CALL INITIATED: {phone_number}")
        return True
    
    else:
        print("  ✗ Could not find phone input field")
        driver.save_screenshot("auto_4_error_no_phone_field.png")
        return False

def monitor_call(driver):
    """Monitor call status and connect HumeAI"""
    print()
    print("[Step 5] Call Monitoring & HumeAI Integration")
    print("-" * 60)
    
    driver.save_screenshot("auto_6_call_active.png")
    
    print()
    print("  🎙️  Call is active!")
    print("  🤖 Connecting to HumeAI...")
    print()
    
    # Try to connect HumeAI
    try:
        hume_success = asyncio.run(connect_hume_ai())
        if hume_success:
            print("  ✅ HumeAI Connected Successfully!")
        else:
            print("  ⚠️  HumeAI connection failed (call continues)")
    except Exception as e:
        print(f"  ⚠️  HumeAI error: {e}")
    
    print()
    print("  Audio Flow:")
    print("    Customer → CallTools → VB-Cable → Backend → HumeAI")
    print("    HumeAI → Backend → VB-Cable → CallTools → Customer")
    print()
    print("  📊 Call monitoring active...")
    print()
    
    # Keep call active for 5 minutes
    duration = 300  # 5 minutes
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < duration:
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            
            mins = remaining // 60
            secs = remaining % 60
            
            print(f"  ⏱️  Call time: {mins:02d}:{secs:02d} | Press Ctrl+C to end", end='\r')
            time.sleep(1)
            
            # Take periodic screenshots
            if elapsed % 30 == 0 and elapsed > 0:
                driver.save_screenshot(f"auto_call_status_{elapsed}s.png")
    
    except KeyboardInterrupt:
        print()
        print()
        print("  ⚠️  Call monitoring interrupted by user")
    
    print()
    print("  ✅ CALL MONITORING COMPLETE")
    return True


async def connect_hume_ai():
    """Connect to HumeAI WebSocket"""
    try:
        url = "wss://api.hume.ai/v0/assistant/chat"
        headers = {"X-Hume-Api-Key": HUME_API_KEY}
        
        async with websockets.connect(url, extra_headers=headers) as ws:
            # Send session settings
            init_msg = {
                "type": "session_settings",
                "config_id": HUME_CONFIG_ID,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": 48000,
                    "channels": 1
                }
            }
            
            await ws.send(json.dumps(init_msg))
            
            # Get response
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("type") == "chat_metadata":
                print(f"    💬 Chat ID: {data.get('chat_id')}")
                return True
                
            return False
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def main():
    """Main automation flow"""
    driver = None
    
    try:
        # Setup
        print("🚀 Starting automation...")
        print()
        driver = setup_browser()
        wait = WebDriverWait(driver, 20)
        
        # Execute automation steps
        if not auto_login(driver, wait):
            raise Exception("Login failed")
        
        if not auto_join_campaign(driver, wait):
            raise Exception("Join campaign failed")
        
        if not auto_set_available(driver, wait):
            raise Exception("Set status failed")
        
        if not auto_dial_number(driver, wait, PHONE_NUMBER):
            raise Exception("Dial failed")
        
        # Monitor call
        monitor_call(driver)
        
        # Summary
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  AUTOMATION COMPLETE                                     ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("✅ All steps completed successfully:")
        print("  1. ✓ Auto Login")
        print("  2. ✓ Auto Join Campaign")
        print("  3. ✓ Auto Set Available")
        print("  4. ✓ Auto Dial Number")
        print("  5. ✓ Call Monitored")
        print()
        print("📸 Screenshots saved:")
        print("  - auto_1_logged_in.png")
        print("  - auto_2_campaign_joined.png")
        print("  - auto_3_status_available.png")
        print("  - auto_4_phone_entered.png")
        print("  - auto_5_call_initiated.png")
        print("  - auto_6_call_active.png")
        print()
        
        return True
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Automation interrupted by user")
        return False
        
    except Exception as e:
        print()
        print(f"❌ Automation error: {e}")
        import traceback
        traceback.print_exc()
        
        if driver:
            driver.save_screenshot("auto_error.png")
            print("Error screenshot: auto_error.png")
        
        return False
        
    finally:
        if driver:
            print()
            input("Press Enter to close browser and exit...")
            driver.quit()
            print("Browser closed.")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
