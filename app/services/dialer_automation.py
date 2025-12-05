"""
Dialer Browser Automation Service
Automatically logs into dialer systems and controls them
Uses Selenium for browser automation (Python 3.13 compatible)
"""
import asyncio
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
import time
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.dialer_user import DialerUser

logger = logging.getLogger(__name__)


class DialerAutomationService:
    """
    Service to automate dialer login and control using Selenium
    Supports multiple dialer types with configurable selectors
    """
    
    def __init__(self):
        self.drivers: Dict[int, webdriver.Chrome] = {}  # user_id -> driver
        
        # Dialer-specific selectors (can be configured per dialer type)
        # Each selector is a list of (By.TYPE, "value") tuples to try in order
        self.selectors = {
            "generic": {
                "username_field": [
                    (By.NAME, "username"),
                    (By.ID, "username"),
                    (By.ID, "user"),
                    (By.XPATH, "//input[@type='text']"),
                ],
                "password_field": [
                    (By.NAME, "password"),
                    (By.ID, "password"),
                    (By.ID, "pass"),
                    (By.XPATH, "//input[@type='password']"),
                ],
                "login_button": [
                    (By.XPATH, "//button[@type='submit']"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Login')]"),
                    (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                ],
                "unpause_button": [
                    (By.XPATH, "//button[contains(text(), 'Unpause')]"),
                    (By.XPATH, "//button[contains(text(), 'Resume')]"),
                    (By.XPATH, "//button[contains(text(), 'Start')]"),
                    (By.ID, "unpause"),
                    (By.CLASS_NAME, "unpause-btn"),
                ],
                "pause_button": [
                    (By.XPATH, "//button[contains(text(), 'Pause')]"),
                    (By.ID, "pause"),
                    (By.CLASS_NAME, "pause-btn"),
                ],
            },
            "vicidial": {
                "username_field": [(By.ID, "AgentUserID")],
                "password_field": [(By.ID, "AgentPassword")],
                "login_button": [(By.ID, "AgentLoginButton")],
                "unpause_button": [(By.XPATH, "//option[@value='RESUME']")],
                "pause_button": [(By.ID, "PauseCodeSelectBox")],
            },
            "goautodial": {
                "username_field": [(By.NAME, "user")],
                "password_field": [(By.NAME, "pass")],
                "login_button": [(By.XPATH, "//button[@type='submit']")],
                "unpause_button": [(By.CLASS_NAME, "resume-btn")],
                "pause_button": [(By.CLASS_NAME, "pause-btn")],
            },
            "calltools": {
                # CallTools (east-1.calltools.io)
                "username_field": [
                    (By.NAME, "username"),
                    (By.ID, "username"),
                    (By.XPATH, "//input[@name='username']"),
                    (By.XPATH, "//input[@type='text']"),
                ],
                "password_field": [
                    (By.NAME, "password"),
                    (By.ID, "password"),
                    (By.XPATH, "//input[@name='password']"),
                    (By.XPATH, "//input[@type='password']"),
                ],
                "login_button": [
                    (By.XPATH, "//button[@type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Login')]"),
                    (By.XPATH, "//button[contains(text(), 'Sign In')]"),
                    (By.XPATH, "//input[@type='submit']"),
                ],
                "unpause_button": [
                    (By.XPATH, "//button[contains(text(), 'Resume')]"),
                    (By.XPATH, "//button[contains(text(), 'Available')]"),
                    (By.ID, "unpause"),
                ],
                "pause_button": [
                    (By.XPATH, "//button[contains(text(), 'Pause')]"),
                    (By.ID, "pause"),
                ],
            },
            "tmdialer": {
                # TM Dialer (tmdialer.gradientconnectedai.com)
                # Welcome screen - Agent Login link
                "agent_login_link": [
                    (By.LINK_TEXT, "Agent Login"),
                    (By.PARTIAL_LINK_TEXT, "Agent"),
                    (By.XPATH, "//a[contains(text(), 'Agent Login')]"),
                    (By.XPATH, "//a[@href*='agc/vicidial.php']"),
                ],
                # Phone Login page (agc/vicidial.php)
                "phone_login_field": [
                    (By.NAME, "phone_login"),
                    (By.XPATH, "//input[@name='phone_login']"),
                    (By.XPATH, "//td[contains(text(), 'Phone Login')]/following-sibling::td/input"),
                ],
                "phone_password_field": [
                    (By.NAME, "phone_pass"),
                    (By.XPATH, "//input[@name='phone_pass']"),
                    (By.XPATH, "//td[contains(text(), 'Phone Password')]/following-sibling::td/input"),
                ],
                "phone_submit_button": [
                    (By.XPATH, "//input[@value='SUBMIT']"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.NAME, "SUBMIT"),
                ],
                # Campaign Login page (second page after phone login)
                "campaign_user_field": [
                    (By.NAME, "VD_login"),
                    (By.XPATH, "//input[@name='VD_login']"),
                    (By.XPATH, "//td[contains(text(), 'User Login')]/following-sibling::td/input"),
                ],
                "campaign_pass_field": [
                    (By.NAME, "VD_pass"),
                    (By.XPATH, "//input[@name='VD_pass']"),
                    (By.XPATH, "//td[contains(text(), 'User Password')]/following-sibling::td/input"),
                ],
                "campaign_dropdown": [
                    (By.NAME, "VD_campaign"),
                    (By.XPATH, "//select[@name='VD_campaign']"),
                    (By.XPATH, "//td[contains(text(), 'Campaign')]/following-sibling::td/select"),
                ],
                "campaign_submit": [
                    (By.XPATH, "//input[@value='SUBMIT']"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.NAME, "SUBMIT"),
                ],
                # Call control buttons (Agent interface)
                "pause_status_button": [
                    # The "ENTER A PAUSE CODE" link - clicking this unpauses the agent
                    (By.LINK_TEXT, "ENTER A PAUSE CODE"),
                    (By.PARTIAL_LINK_TEXT, "PAUSE CODE"),
                    (By.XPATH, "//a[contains(text(), 'PAUSE CODE')]"),
                    # Fallback selectors
                    (By.XPATH, "//*[contains(text(), 'YOU ARE PAUSED')]"),
                    (By.XPATH, "//span[contains(text(), 'PAUSED')]"),
                ],
                "unpause_button": [
                    (By.LINK_TEXT, "ENTER A PAUSE CODE"),  # Main selector for TM Dialer
                    (By.XPATH, "//a[contains(text(), 'PAUSE CODE')]"),
                    (By.XPATH, "//span[contains(text(), 'YOU ARE PAUSED')]"),
                    (By.XPATH, "//button[contains(text(), 'Ready')]"),
                    (By.XPATH, "//button[contains(text(), 'Unpause')]"),
                    (By.ID, "PauseCodeSpan"),
                ],
                "pause_button": [
                    (By.XPATH, "//button[contains(text(), 'Pause')]"),
                    (By.ID, "pause"),
                ],
            }
        }
    
    async def initialize(self):
        """Initialize Chrome driver manager"""
        try:
            # Pre-download ChromeDriver
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, ChromeDriverManager().install)
            logger.info("Browser automation initialized successfully (Selenium)")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all browser instances"""
        try:
            # Close all drivers
            for driver in self.drivers.values():
                try:
                    await asyncio.to_thread(driver.quit)
                except:
                    pass
            
            self.drivers.clear()
            logger.info("Browser automation shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _create_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Create new Chrome driver instance"""
        import tempfile
        
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Use fresh Chrome profile to avoid password popups
        user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_")
        options.add_argument(f'--user-data-dir={user_data_dir}')
        
        # Auto-allow microphone and disable password prompts
        options.add_argument('--use-fake-ui-for-media-stream')
        options.add_argument('--use-fake-device-for-media-stream')
        options.add_argument('--disable-save-password-bubble')
        options.add_argument('--disable-features=PasswordManager')
        options.add_argument('--password-store=basic')
        
        # Disable automation detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Comprehensive password manager disable preferences
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "autofill.profile_enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        return driver
    
    def _find_element(self, driver: webdriver.Chrome, selectors: list, timeout: int = 10):
        """Try multiple selectors to find element"""
        for by, value in selectors:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except TimeoutException:
                continue
        raise NoSuchElementException(f"Could not find element with any selector")
    
    async def login_dialer(
        self, 
        db: AsyncSession, 
        user_id: int,
        headless: bool = True
    ) -> bool:
        """
        Log into dialer system with user credentials
        
        Args:
            db: Database session
            user_id: Dialer user ID
            headless: Run browser in headless mode
            
        Returns:
            bool: True if login successful
        """
        try:
            # Get user from database
            result = await db.execute(
                select(DialerUser).where(DialerUser.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"Dialer user {user_id} not found")
                return False
            
            if not user.is_active:
                logger.warning(f"Dialer user {user_id} is inactive")
                return False
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None, 
                self._login_sync, 
                user, 
                user_id, 
                headless
            )
            
            if success:
                # Update database
                await db.execute(
                    update(DialerUser)
                    .where(DialerUser.id == user_id)
                    .values(
                        is_logged_in=True,
                        last_login=datetime.utcnow(),
                        session_id=f"selenium_{user_id}"
                    )
                )
                await db.commit()
            
            return success
                
        except Exception as e:
            logger.error(f"Error during login for user {user_id}: {e}")
            return False
    
    def _login_sync(self, user: DialerUser, user_id: int, headless: bool) -> bool:
        """Synchronous login logic"""
        try:
            # Create new driver
            driver = self._create_driver(headless)
            self.drivers[user_id] = driver
            
            # Navigate to dialer URL
            logger.info(f"Navigating to dialer: {user.dialer_url}")
            driver.get(user.dialer_url)
            
            # Wait for page load
            time.sleep(2)
            
            # Get selectors for this dialer type
            selectors = self.selectors.get(user.dialer_type, self.selectors["generic"])
            
            # ===== CALLTOOLS: Simple username/password login =====
            if user.dialer_type == "calltools":
                logger.info("[CallTools Login] Starting simple login flow")
                
                # Find and fill username
                logger.info(f"[CallTools Login] Filling username: {user.username}")
                username_field = self._find_element(driver, selectors["username_field"])
                username_field.clear()
                username_field.send_keys(user.username)
                
                # Find and fill password
                logger.info(f"[CallTools Login] Filling password")
                password_field = self._find_element(driver, selectors["password_field"])
                password_field.clear()
                password_field.send_keys(user.password)
                
                # Click login button
                logger.info("[CallTools Login] Clicking login button")
                login_button = self._find_element(driver, selectors["login_button"])
                login_button.click()
                
                # Wait for navigation
                logger.info("[CallTools Login] Waiting for dashboard to load...")
                time.sleep(5)
                
                logger.info("[CallTools Login] Login complete! ✅")
                return True
            
            # ===== TM DIALER: Click "Agent Login" link first =====
            if user.dialer_type == "tmdialer":
                logger.info("[Welcome Page] Looking for 'Agent Login' link")
                try:
                    agent_login_link = self._find_element(driver, selectors["agent_login_link"], timeout=5)
                    agent_login_link.click()
                    logger.info("[Welcome Page] Clicked 'Agent Login' link")
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"[Welcome Page] Could not find Agent Login link: {e}")
                    # Continue anyway in case already on login page
            
            # ===== PHONE LOGIN PAGE (after Agent Login click) =====
            # Find and fill Phone Login (1004)
            logger.info(f"[Phone Login Page] Filling Phone Login: {user.username}")
            phone_login_field = self._find_element(driver, selectors["phone_login_field"])
            phone_login_field.clear()
            phone_login_field.send_keys(user.username)  # 1004
            
            # Find and fill Phone Password (tmai)
            phone_password_field = self._find_element(driver, selectors["phone_password_field"])
            phone_password_field.clear()
            phone_password_field.send_keys(user.password)  # tmai
            
            # Click SUBMIT button
            logger.info("[Phone Login Page] Clicking SUBMIT button")
            phone_submit_button = self._find_element(driver, selectors["phone_submit_button"])
            phone_submit_button.click()
            
            # Wait for navigation
            time.sleep(3)
            
            # ===== CAMPAIGN LOGIN PAGE (second page after phone login) =====
            if user.dialer_type == "tmdialer":
                logger.info("[Campaign Login Page] Looking for campaign selection page...")
                
                try:
                    # Find User Login field
                    campaign_user_field = self._find_element(driver, selectors.get("campaign_user_field", []), timeout=5)
                    logger.info("[Campaign Login Page] Found - filling credentials")
                    
                    # Fill User Login (1004)
                    campaign_user_field.clear()
                    campaign_user_field.send_keys(user.username)  # 1004
                    logger.info(f"[Campaign Login Page] Filled User Login: {user.username}")
                    
                    # Fill User Password (1004)
                    campaign_pass_field = self._find_element(driver, selectors["campaign_pass_field"])
                    campaign_pass_field.clear()
                    campaign_pass_field.send_keys(user.username)  # 1004 (same as username)
                    logger.info("[Campaign Login Page] Filled User Password")
                    
                    # Wait before selecting campaign
                    time.sleep(1)
                    
                    # Select Campaign from dropdown
                    try:
                        from selenium.webdriver.support.ui import Select
                        
                        # Find dropdown and select
                        campaign_dropdown = self._find_element(driver, selectors["campaign_dropdown"])
                        select = Select(campaign_dropdown)
                        
                        # Get all available campaigns
                        options = select.options
                        logger.info(f"[Campaign Login Page] Found {len(options)} options in dropdown")
                        
                        if len(options) > 1:
                            # Select first actual campaign (skip "-- PLEASE SELECT A CAMPAIGN --")
                            select.select_by_index(1)
                            logger.info(f"[Campaign Login Page] Selected campaign: {options[1].text}")
                            time.sleep(1)
                        else:
                            logger.warning("[Campaign Login Page] No campaigns available in dropdown")
                    except Exception as e:
                        logger.warning(f"[Campaign Login Page] Could not select campaign: {e}")
                    
                    # Click SUBMIT
                    campaign_submit = self._find_element(driver, selectors["campaign_submit"])
                    campaign_submit.click()
                    
                    logger.info("[Campaign Login Page] Submitted - waiting for agent interface...")
                    time.sleep(5)  # Wait longer for agent interface to load
                    
                except Exception as e:
                    logger.warning(f"[Campaign Login Page] Not found or failed: {e}")
                    # Continue - might already be logged in
            
            # ===== HANDLE DUPLICATE SESSION POPUP (if appears) =====
            if user.dialer_type == "tmdialer":
                logger.info("[Agent Interface] Checking for duplicate session popup...")
                
                try:
                    # Look for "OK" link to dismiss "Another live agent session was open" message
                    ok_link = self._find_element(driver, [(By.LINK_TEXT, "OK"), (By.PARTIAL_LINK_TEXT, "OK")], timeout=3)
                    
                    if ok_link:
                        logger.info("[Agent Interface] Found duplicate session popup - clicking OK...")
                        ok_link.click()
                        time.sleep(2)
                        logger.info("✅ Dismissed duplicate session warning")
                    
                except Exception as e:
                    logger.info("[Agent Interface] No duplicate session popup (continuing)")
                
                # Close password popup using PyAutoGUI (if not headless)
                if not headless:
                    try:
                        import pyautogui
                        time.sleep(2)
                        
                        screen_width, screen_height = pyautogui.size()
                        center_x, center_y = screen_width // 2, screen_height // 2
                        
                        # Click center to close password popup
                        pyautogui.click(center_x, center_y)
                        logger.info("Attempted to close password popup with PyAutoGUI")
                        time.sleep(1)
                    except Exception as e:
                        logger.warning(f"Could not use PyAutoGUI: {e}")
                
                # Handle browser permission popups
                try:
                    # Microphone permission
                    allow_btn = self._find_element(driver, [(By.XPATH, "//button[contains(text(), 'Allow this time')]")], timeout=2)
                    if allow_btn:
                        allow_btn.click()
                        logger.info("✅ Allowed microphone permission")
                        time.sleep(1)
                except:
                    pass
                
                try:
                    # Any OK button for browser popups
                    ok_btn = self._find_element(driver, [(By.XPATH, "//button[contains(text(), 'OK')]")], timeout=2)
                    if ok_btn:
                        ok_btn.click()
                        logger.info("✅ Dismissed browser popup")
                        time.sleep(1)
                except:
                    pass
            
            # ===== AUTO-UNPAUSE (Click "YOU ARE PAUSED" button) =====
            if user.dialer_type == "tmdialer" and user.auto_unpause:
                logger.info("[Agent Interface] Checking for pause status...")
                
                try:
                    # Wait a bit more for interface to fully load
                    time.sleep(2)
                    
                    # Look for pause-related elements
                    pause_button = None
                    
                    # Method 1: Look for "YOU ARE PAUSED" text anywhere
                    try:
                        all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'YOU ARE PAUSED')]")
                        for elem in all_elements:
                            if elem.is_displayed() and "YOU ARE PAUSED" in elem.text:
                                pause_button = elem
                                logger.info(f"Found 'YOU ARE PAUSED' button (tag: {elem.tag_name})")
                                break
                    except:
                        pass
                    
                    # Method 2: Look for "ENTER A PAUSE CODE" link
                    if not pause_button:
                        pause_elements = driver.find_elements(By.PARTIAL_LINK_TEXT, "PAUSE")
                        for elem in pause_elements:
                            if elem.is_displayed():
                                elem_text = elem.text.strip()
                                if "YOU ARE PAUSED" in elem_text or "ENTER A PAUSE CODE" in elem_text:
                                    pause_button = elem
                                    logger.info(f"Found pause element: '{elem_text}'")
                                    break
                    
                    if pause_button:
                        logger.info("[Agent Interface] Clicking pause button to unpause...")
                        try:
                            # Try normal click first
                            pause_button.click()
                            logger.info("✅ Clicked pause button (normal click)")
                        except Exception as click_error:
                            # Fallback to JavaScript click
                            logger.info(f"Normal click failed, trying JavaScript click...")
                            driver.execute_script("arguments[0].click();", pause_button)
                            logger.info("✅ Clicked pause button via JavaScript")
                        
                        time.sleep(3)
                        
                        # Verify unpause worked
                        try:
                            paused_check = driver.find_elements(By.XPATH, "//*[contains(text(), 'YOU ARE PAUSED')]")
                            if len(paused_check) == 0 or not any(e.is_displayed() for e in paused_check):
                                logger.info("✅ Agent successfully unpaused - 'YOU ARE PAUSED' button disappeared")
                            else:
                                logger.warning("⚠ Agent may still be paused")
                        except:
                            logger.info("Unpause attempted (verification skipped)")
                    else:
                        logger.info("[Agent Interface] No pause button found - agent might already be active")
                        
                except Exception as e:
                    logger.warning(f"[Agent Interface] Could not handle pause button: {e}")
                    # Continue - agent might already be unpaused
            
            # Check if login was successful
            current_url = driver.current_url
            page_source = driver.page_source.lower()
            
            # Success indicators
            success_indicators = [
                "dashboard" in current_url.lower(),
                "agent" in current_url.lower(),
                "campaign" in page_source,
                "logout" in page_source,
                "pause" in page_source,
                "ready" in page_source
            ]
            
            if any(success_indicators):
                logger.info(f"✅ Login successful for user {user.username}")
                return True
            else:
                logger.error(f"❌ Login failed for user {user.username}")
                return False
                
        except Exception as e:
            logger.error(f"Login sync error: {e}")
            # Cleanup on failure
            if user_id in self.drivers:
                try:
                    self.drivers[user_id].quit()
                    del self.drivers[user_id]
                except:
                    pass
            return False
    
    async def click_unpause(self, db: AsyncSession, user_id: int) -> bool:
        """
        Click the unpause/resume button on dialer
        
        Args:
            db: Database session
            user_id: Dialer user ID
            
        Returns:
            bool: True if unpause successful
        """
        try:
            # Check if user has active driver
            driver = self.drivers.get(user_id)
            if not driver:
                logger.error(f"No active session for user {user_id}")
                return False
            
            # Get user info
            result = await db.execute(
                select(DialerUser).where(DialerUser.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Run in executor
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self._click_unpause_sync,
                driver,
                user
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error clicking unpause for user {user_id}: {e}")
            return False
    
    def _click_unpause_sync(self, driver: webdriver.Chrome, user: DialerUser) -> bool:
        """Synchronous unpause logic"""
        try:
            selectors = self.selectors.get(user.dialer_type, self.selectors["generic"])
            
            logger.info(f"Looking for unpause button for user {user.username}")
            unpause_button = self._find_element(driver, selectors["unpause_button"])
            unpause_button.click()
            
            logger.info(f"Unpause button clicked for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Unpause sync error: {e}")
            return False
    
    async def click_pause(self, db: AsyncSession, user_id: int) -> bool:
        """
        Click the pause button on dialer
        
        Args:
            db: Database session
            user_id: Dialer user ID
            
        Returns:
            bool: True if pause successful
        """
        try:
            driver = self.drivers.get(user_id)
            if not driver:
                logger.error(f"No active session for user {user_id}")
                return False
            
            result = await db.execute(
                select(DialerUser).where(DialerUser.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self._click_pause_sync,
                driver,
                user
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error clicking pause for user {user_id}: {e}")
            return False
    
    def _click_pause_sync(self, driver: webdriver.Chrome, user: DialerUser) -> bool:
        """Synchronous pause logic"""
        try:
            selectors = self.selectors.get(user.dialer_type, self.selectors["generic"])
            
            logger.info(f"Looking for pause button for user {user.username}")
            pause_button = self._find_element(driver, selectors["pause_button"])
            pause_button.click()
            
            logger.info(f"Pause button clicked for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Pause sync error: {e}")
            return False
    
    async def logout_dialer(self, db: AsyncSession, user_id: int) -> bool:
        """
        Logout from dialer and close browser session
        
        Args:
            db: Database session
            user_id: Dialer user ID
            
        Returns:
            bool: True if logout successful
        """
        try:
            # Close driver
            driver = self.drivers.pop(user_id, None)
            if driver:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, driver.quit)
            
            # Update database
            await db.execute(
                update(DialerUser)
                .where(DialerUser.id == user_id)
                .values(is_logged_in=False, session_id=None)
            )
            await db.commit()
            
            logger.info(f"User {user_id} logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during logout for user {user_id}: {e}")
            return False
    
    async def take_screenshot(self, user_id: int, path: str) -> bool:
        """Take screenshot of current page for debugging"""
        try:
            driver = self.drivers.get(user_id)
            if driver:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, driver.save_screenshot, path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return False
    
    async def login_with_retry(
        self,
        db: AsyncSession,
        user_id: int,
        max_retries: int = 3,
        headless: bool = True
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Login with exponential backoff retry mechanism
        
        Args:
            db: Database session
            user_id: Dialer user ID
            max_retries: Maximum number of retry attempts
            headless: Run browser in headless mode
            
        Returns:
            Tuple of (success, attempts, error_message)
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Login attempt {attempt}/{max_retries} for user {user_id}")
                
                # Try to login
                success = await self.login_dialer(db, user_id, headless)
                
                if success:
                    logger.info(f"Login successful on attempt {attempt}")
                    return (True, attempt, None)
                
                last_error = "Login failed - credentials or selectors issue"
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Login attempt {attempt} failed: {e}")
                
                # Clean up failed driver
                if user_id in self.drivers:
                    try:
                        driver = self.drivers.pop(user_id)
                        await asyncio.to_thread(driver.quit)
                    except:
                        pass
            
            # Don't wait after last attempt
            if attempt < max_retries:
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f} seconds before retry")
                await asyncio.sleep(wait_time)
        
        logger.error(f"Login failed after {max_retries} attempts")
        return (False, max_retries, last_error)
    
    async def reconnect_if_disconnected(
        self,
        db: AsyncSession,
        user_id: int
    ) -> bool:
        """
        Check if session is still active, reconnect if needed
        
        Returns:
            bool: True if connected (or reconnected successfully)
        """
        try:
            driver = self.drivers.get(user_id)
            
            if not driver:
                logger.warning(f"No driver for user {user_id}, attempting reconnect")
                success, _, _ = await self.login_with_retry(db, user_id, max_retries=2)
                return success
            
            # Check if driver is still responsive
            try:
                current_url = await asyncio.to_thread(lambda: driver.current_url)
                logger.debug(f"Driver for user {user_id} is responsive: {current_url}")
                return True
            except Exception as e:
                logger.warning(f"Driver unresponsive for user {user_id}: {e}")
                
                # Clean up dead driver
                try:
                    self.drivers.pop(user_id)
                    await asyncio.to_thread(driver.quit)
                except:
                    pass
                
                # Attempt reconnect
                logger.info(f"Attempting to reconnect user {user_id}")
                success, _, _ = await self.login_with_retry(db, user_id, max_retries=2)
                return success
                
        except Exception as e:
            logger.error(f"Error checking connection for user {user_id}: {e}")
            return False
    
    async def health_check(self, user_id: int) -> Dict:
        """
        Check health of browser session
        
        Returns:
            Dict with status information
        """
        driver = self.drivers.get(user_id)
        
        if not driver:
            return {
                "status": "disconnected",
                "has_driver": False,
                "responsive": False
            }
        
        try:
            # Test if driver is responsive
            current_url = await asyncio.to_thread(lambda: driver.current_url)
            window_handles = await asyncio.to_thread(lambda: len(driver.window_handles))
            
            return {
                "status": "connected",
                "has_driver": True,
                "responsive": True,
                "current_url": current_url,
                "windows": window_handles
            }
        except Exception as e:
            return {
                "status": "error",
                "has_driver": True,
                "responsive": False,
                "error": str(e)
            }


# Global instance
dialer_automation = DialerAutomationService()
