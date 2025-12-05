"""
DEBUG CallTools Login
=====================
Opens browser and attempts login, then waits so you can see what's wrong
"""

import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CALLTOOLS_URL = "https://east-1.calltools.io"
CALLTOOLS_USERNAME = "Eddie.Faklis"
CALLTOOLS_PASSWORD = "Roofing123"


async def debug_login():
    """Debug login process"""
    
    # Setup Chrome - WITH visible browser
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    try:
        print("\n" + "=" * 60)
        print("🔍 DEBUG MODE - Login Process")
        print("=" * 60 + "\n")
        
        # Step 1: Open page
        print(f"📂 Opening: {CALLTOOLS_URL}")
        driver.get(CALLTOOLS_URL)
        
        wait = WebDriverWait(driver, 20)
        await asyncio.sleep(3)
        
        # Step 2: Find and fill username
        print("🔍 Looking for username field...")
        username_field = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.clear()
        username_field.send_keys(CALLTOOLS_USERNAME)
        print(f"✅ Username entered: {CALLTOOLS_USERNAME}")
        
        # Step 3: Find and fill password
        print("🔍 Looking for password field...")
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(CALLTOOLS_PASSWORD)
        print("✅ Password entered")
        
        # Step 4: Find and click login button
        print("🔍 Looking for login button...")
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        print("✅ Login button found")
        
        await asyncio.sleep(1)
        login_button.click()
        print("✅ Login button clicked!")
        
        # Wait and check
        print("\n⏳ Waiting 8 seconds for response...\n")
        await asyncio.sleep(8)
        
        # Check result
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        # Check for error messages
        try:
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert, .error, .warning, [role='alert']")
            if error_elements:
                print("\n⚠️ ERROR MESSAGES FOUND:")
                for elem in error_elements:
                    text = elem.text.strip()
                    if text:
                        print(f"   ❌ {text}")
        except:
            pass
        
        # Check page title
        print(f"📄 Page Title: {driver.title}")
        
        # Check if still on login
        if "login" in current_url.lower():
            print("\n❌ STILL ON LOGIN PAGE")
            print("\n💡 Possible reasons:")
            print("   1. Wrong username or password")
            print("   2. Account locked or disabled")
            print("   3. CAPTCHA required")
            print("   4. IP blocked")
            print("   5. Additional authentication required")
        else:
            print("\n✅ LOGIN SUCCESSFUL!")
            print(f"   Redirected to: {current_url}")
        
        # Keep browser open for manual inspection
        print("\n" + "=" * 60)
        print("🔍 BROWSER WILL STAY OPEN FOR 60 SECONDS")
        print("   Check the browser for:")
        print("   • Error messages")
        print("   • CAPTCHA")
        print("   • Security warnings")
        print("   • Any popups or alerts")
        print("=" * 60 + "\n")
        
        print("⏰ Waiting 60 seconds...")
        for i in range(60, 0, -10):
            print(f"   {i} seconds remaining...")
            await asyncio.sleep(10)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n⏸️ Browser will stay open for 30 seconds so you can inspect...")
        await asyncio.sleep(30)
    
    finally:
        print("\n🧹 Closing browser...")
        driver.quit()
        print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(debug_login())
