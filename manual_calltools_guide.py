"""
CallTools Manual Guide Script
Opens browser and pauses at each step for you to manually complete
Then takes screenshot to help identify correct selectors
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"

print("╔══════════════════════════════════════════════════════════╗")
print("║  CallTools Manual Login Helper                          ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print("This script will open CallTools and pause at each step.")
print("You manually complete each step, then press Enter.")
print("Screenshots will be taken to identify correct selectors.")
print()

options = webdriver.ChromeOptions()
options.add_argument('--start-maximized')

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    # Step 1
    print(f"[Step 1] Opening {CALLTOOLS_URL}...")
    driver.get(CALLTOOLS_URL)
    driver.save_screenshot("manual_1_homepage.png")
    print("✓ Homepage loaded")
    print()
    print("👉 MANUAL ACTION NEEDED:")
    print("   - Look at the homepage")
    print("   - Find the login area")
    input("Press Enter when ready to continue...")
    
    # Step 2
    print()
    print("[Step 2] Login Page")
    driver.save_screenshot("manual_2_login_page.png")
    print()
    print("👉 MANUAL ACTION NEEDED:")
    print(f"   - Enter username: {USERNAME}")
    print(f"   - Enter password: {PASSWORD}")
    print("   - Click Login button")
    print("   - Complete login")
    input("Press Enter after you've logged in...")
    
    # Step 3
    driver.save_screenshot("manual_3_after_login.png")
    print()
    print("[Step 3] After Login")
    print()
    print("👉 MANUAL ACTION NEEDED:")
    print("   - Look for 'Join Campaign' button")
    print("   - Click it if you see it")
    input("Press Enter after joining campaign (or skip if not needed)...")
    
    # Step 4
    driver.save_screenshot("manual_4_campaign_joined.png")
    print()
    print("[Step 4] Campaign Status")
    print()
    print("👉 MANUAL ACTION NEEDED:")
    print("   - Find status dropdown or button")
    print("   - Change status to 'Available'")
    input("Press Enter after status is Available...")
    
    # Step 5
    driver.save_screenshot("manual_5_status_available.png")
    print()
    print("[Step 5] Ready to Dial")
    print()
    print("👉 MANUAL ACTION NEEDED:")
    print(f"   - Find phone number input field")
    print(f"   - Enter: {PHONE_NUMBER}")
    print("   - Look for 'Call' or 'Dial' button")
    print("   - DO NOT CLICK YET")
    input("Press Enter when phone number is entered...")
    
    # Step 6
    driver.save_screenshot("manual_6_phone_entered.png")
    print()
    print("[Step 6] Ready to Call")
    print()
    print("👉 MANUAL ACTION NEEDED:")
    print(f"   - Now click 'Call' or 'Dial' button")
    print(f"   - This will initiate call to {PHONE_NUMBER}")
    input("Press Enter after clicking Call...")
    
    # Step 7
    driver.save_screenshot("manual_7_call_initiated.png")
    print()
    print("[Step 7] Call In Progress")
    driver.save_screenshot("manual_8_final_state.png")
    
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Screenshots Saved!                                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("📸 Screenshots saved:")
    print("   - manual_1_homepage.png")
    print("   - manual_2_login_page.png")
    print("   - manual_3_after_login.png")
    print("   - manual_4_campaign_joined.png")
    print("   - manual_5_status_available.png")
    print("   - manual_6_phone_entered.png")
    print("   - manual_7_call_initiated.png")
    print("   - manual_8_final_state.png")
    print()
    print("These screenshots will help me identify the correct")
    print("HTML elements to automate the process.")
    print()
    print("Browser will stay open...")
    input("Press Enter to close browser...")
    
except Exception as e:
    print(f"Error: {e}")
    driver.save_screenshot("manual_error.png")
    
finally:
    driver.quit()
    print("Browser closed.")
