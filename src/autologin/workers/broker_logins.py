"""
Broker login functions using Playwright.
Each function is async and uses Playwright Page for browser automation.
Ported from the original Selenium implementations with exact XPath selectors preserved.
"""

import asyncio
import base64
import hashlib
import json
import logging
import pyotp
import requests
from playwright.async_api import Page

from autologin.utils.api import generate_dhan_consent, get_auto_code_fyers
from autologin.workers.playwright_driver import (
    wait_and_fill,
    wait_and_click,
    wait_for_text,
    check_page_contains,
)


FYERS_APP_ID = "YPUVOWAXFE-100"


def _generate_totp(secret: str) -> str:
    """Generate TOTP code from secret."""
    return pyotp.TOTP(secret).now()


async def run_angel_one_login(page: Page, account: dict) -> dict:
    """
    Login to Angel One broker account.
    """
    try:
        client_id = account['client_id'].strip()
        mpin = account['mpin'].strip()
        totp_key = account['totp_key'].strip()
        
        url = "https://smartapi.angelbroking.com/publisher-login?api_key=oS35ILQ1"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Click TOTP radio button
        await wait_and_click(page, '#login-by-totp')
        
        # Fill client ID
        await wait_and_fill(page, '#tot-user-id-block input', client_id)
        
        # Fill MPIN
        await wait_and_fill(page, '#tot-pin', mpin)
        
        # Fill TOTP
        otp = _generate_totp(totp_key)
        await wait_and_fill(page, '#tot-totp', otp)
        
        # Click login button
        await wait_and_click(page, '#totp-login div')
        
        # Wait for success
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Angel One login error: {e}")
        return {"status": False, "message": str(e)}


async def run_zerodha_login(page: Page, account: dict) -> dict:
    """
    Login to Zerodha (Kite) broker account.
    """
    try:
        api_key = account['api_key'].strip()
        client_id = account['client_id'].strip()
        password = account['password'].strip()
        totp_key = account['totp_key'].strip()
        
        url = f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}&redirect_params=account_id%3D{client_id}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill user ID
        await wait_and_fill(page, '#userid', client_id)
        
        # Fill password
        await wait_and_fill(page, '#password', password)
        
        # Click login button
        await wait_and_click(page, '.button-orange')
        
        await asyncio.sleep(2)
        
        # Fill TOTP
        otp = _generate_totp(totp_key)
        await wait_and_fill(page, 'input[label="External TOTP"]', otp)
        
        # Wait for success
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Zerodha login error: {e}")
        return {"status": False, "message": str(e)}


async def run_upstox_login(page: Page, account: dict) -> dict:
    """
    Login to Upstox broker account.
    Uses exact selectors from original Selenium implementation.
    """
    try:
        client_id = account['client_id'].strip()
        api_key = account['api_key'].strip()
        mpin = account['mpin'].strip()
        totp_key = account['totp_key'].strip()
        mobile_no = account['mobile_number'].strip()
        
        url = f"https://api-v2.upstox.com/login/authorization/dialog?response_type=code&client_id={api_key}&redirect_uri=https://cirrus.trade/add-broker-account/upstox&state={client_id}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill mobile number (by id)
        mobile_field = await page.wait_for_selector('#mobileNum', timeout=10000)
        await mobile_field.click()
        await mobile_field.type(mobile_no)
        
        # Click Get OTP (by id)
        get_otp_btn = await page.wait_for_selector('#getOtp', timeout=10000)
        await get_otp_btn.click()
        
        await asyncio.sleep(2)
        
        # Fill OTP (TOTP) (by id)
        otp = _generate_totp(totp_key)
        otp_field = await page.wait_for_selector('#otpNum', timeout=10000)
        await otp_field.click()
        await otp_field.type(otp)
        
        # Wait for PIN field with retry
        pin_field = None
        for _ in range(3):
            try:
                pin_field = await page.wait_for_selector('xpath=//*[@id="pinCode"]', timeout=10000)
                if pin_field:
                    break
            except Exception:
                await asyncio.sleep(10)
                continue
        
        if not pin_field:
            return {"status": False, "message": "PIN Field not found"}
        
        await pin_field.click()
        await pin_field.type(mpin)
        
        # Click continue (by id)
        continue_btn = await page.wait_for_selector('#pinContinueBtn', timeout=10000)
        await continue_btn.click()
        
        # Wait for success
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Upstox login error: {e}")
        return {"status": False, "message": str(e)}


async def run_sharekhan_login(page: Page, account: dict) -> dict:
    """
    Login to Sharekhan broker account.
    Uses exact selectors from original Selenium implementation.
    """
    try:
        client_id = account['client_id'].strip()
        api_key = account['api_key'].strip()
        password = account['password'].strip()
        totp_key = account['totp_key'].strip()
        
        url = f"https://api.sharekhan.com/skapi/auth/login.html?api_key={api_key}&state={client_id}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill password (by id)
        password_field = await page.wait_for_selector('#mpwd', timeout=10000)
        await password_field.click()
        await password_field.type(password)
        
        # Click login (by id)
        login_btn = await page.wait_for_selector('#lg_btn', timeout=10000)
        await login_btn.click()
        
        await asyncio.sleep(3)
        
        # Switch to TOTP if needed (exact xpath from original)
        try:
            otp_switch = await page.wait_for_selector(
                'xpath=/html/body/div[2]/div/div/div/form[2]/span[2]/a',
                timeout=10000
            )
            text = await otp_switch.text_content()
            if text == "Switch to TOTP":
                await otp_switch.click()
        except Exception:
            pass
        
        # Fill TOTP (by id)
        totp_field = await page.wait_for_selector('#totp', timeout=10000)
        current_otp = _generate_totp(totp_key)
        await totp_field.type(current_otp)
        
        # Click submit (exact xpath from original)
        submit_btn = await page.wait_for_selector(
            'xpath=/html/body/div[2]/div/div/div/form[3]/div/button',
            timeout=10000
        )
        await submit_btn.click()
        
        # Wait for success
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Sharekhan login error: {e}")
        return {"status": False, "message": str(e)}


async def run_motilaloswal_login(page: Page, account: dict) -> dict:
    """
    Login to Motilal Oswal broker account.
    Uses API-based login (same as original).
    """
    try:
        client_id = account['client_id'].strip()
        api_key = account['api_key'].strip()
        password = account['password'].strip()
        totp_key = account['totp_key'].strip()
        dob = account.get('dob', '').strip()
        
        # API-based authentication (same as original)
        url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"
        combine = password + api_key
        h = hashlib.sha256(combine.encode("utf-8"))
        checksum = h.hexdigest()
        
        current_otp = _generate_totp(totp_key)
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MOSL/V.1.1.0",
            "sourceid": "web",
            "macaddress": "00:00:00:00:00:00",
            "clientlocalip": "127.0.0.1",
            "clientpublicip": "1.2.3.4",
            "vendorinfo": client_id,
            "ApiKey": api_key,
            "osname": "Windows 10",
            "osversion": "10.0.19041",
            "devicemodel": "AHV",
            "manufacturer": "DELL",
            "browsername": "Chrome",
            "browserversion": "135.0",
            "productname": "Investor",
            "productversion": "1",
        }
        
        payload = {
            "userid": client_id,
            "password": checksum,
            "2FA": dob,
            "totp": current_otp
        }
        
        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        resp_json = resp.json()
        
        if resp_json.get('status') != 'SUCCESS' or not resp_json.get('AuthToken'):
            return {"status": False, "message": "Invalid Credentials"}
        
        # Navigate to save account
        return_url = f"https://cirrus.tradinx.in/add-broker-account/motilal-oswal?authtoken={resp_json['AuthToken']}&state={client_id}"
        await page.goto(return_url, wait_until='domcontentloaded')
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Motilal Oswal login error: {e}")
        return {"status": False, "message": str(e)}


async def run_nuvama_login(page: Page, account: dict) -> dict:
    """
    Login to Nuvama broker account.
    Uses exact XPath selectors from original Selenium implementation.
    """
    try:
        client_id = account['client_id'].strip()
        password = account['password'].strip()
        totp_key = account['totp_key'].strip()
        
        # Fetch session token
        request_url = "https://api.cirrus.trade/settings/fetch_nuvama_session_token"
        req = requests.get(request_url, headers={'Accept-Encoding': 'application/json'})
        resp = req.json()
        session_token = resp['data']
        
        url = f"https://www.nuvamawealth.com/login?ordsrc=cirrus&ordsrctkn={session_token}&state={client_id}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill client ID (by id)
        client_id_field = await page.wait_for_selector('#userID', timeout=10000)
        await client_id_field.click()
        await client_id_field.type(client_id)
        
        # Click login (exact xpath from original)
        login_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/div/button',
            timeout=10000
        )
        await login_btn.click()
        
        # Handle equity selection if present (exact xpaths from original)
        try:
            equity_btn = await page.wait_for_selector(
                'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[1]/div[1]',
                timeout=6000
            )
            await equity_btn.click()
            
            continue_btn = await page.wait_for_selector(
                'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/button',
                timeout=6000
            )
            await continue_btn.click()
        except Exception:
            pass
        
        # Fill password (exact xpath from original)
        password_field = await page.wait_for_selector(
            'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/div[1]/input',
            timeout=10000
        )
        await password_field.click()
        await password_field.type(password)
        
        # Click continue (exact xpath from original)
        continue_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/div[3]/button',
            timeout=10000
        )
        await continue_btn.click()
        
        # Check if we need to switch to External TOTP (exact xpath from original)
        try:
            text_elem = await page.wait_for_selector(
                'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[1]/div',
                timeout=10000
            )
            text = await text_elem.text_content()
            if text == "Mobile App Code":
                external_totp_btn = await page.wait_for_selector(
                    'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[3]/div[1]',
                    timeout=10000
                )
                await external_totp_btn.click()
        except Exception:
            pass
        
        # Fill TOTP (6 separate fields with exact xpaths from original)
        current_otp = _generate_totp(totp_key)
        totp_xpaths = [
            '/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/input[1]',
            '/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/input[2]',
            '/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/input[3]',
            '/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/input[4]',
            '/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/input[5]',
            '/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[1]/div[2]/input[6]',
        ]
        
        for i, xpath in enumerate(totp_xpaths):
            field = await page.wait_for_selector(f'xpath={xpath}', timeout=10000)
            await field.click()
            await field.type(current_otp[i])
        
        # Click proceed (exact xpath from original)
        proceed_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div[1]/div/form/div[2]/div/div[2]/button',
            timeout=10000
        )
        await proceed_btn.click()
        
        # Click submit (exact xpath from original)
        submit_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div[2]/ui-view/div/div[2]/div/div/div/div/form/div[3]/button',
            timeout=10000
        )
        await submit_btn.click()
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Nuvama login error: {e}")
        return {"status": False, "message": str(e)}


async def run_jainam_lite_login(page: Page, account: dict) -> dict:
    """
    Login to Jainam Lite broker account.
    Uses exact XPath selectors from original Selenium implementation.
    """
    try:
        client_id = account['client_id'].strip()
        password = account['password'].strip()
        totp_key = account['totp_key'].strip()
        
        url = "https://protrade.jainam.in/?appcode=voMBqocRqgqIdpi"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill user ID (exact xpath from original)
        user_id_field = await page.wait_for_selector(
            'xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div/div[1]/div/form/div/div[2]/div[1]/div/input',
            timeout=10000
        )
        await user_id_field.click()
        await user_id_field.type(client_id)
        
        # Click continue (exact xpath from original)
        continue_btn = await page.wait_for_selector(
            'xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div/div[1]/div/form/div/div[2]/div[2]/button',
            timeout=10000
        )
        await continue_btn.click()
        
        await asyncio.sleep(2)
        
        # Fill password (exact xpath from original)
        password_field = await page.wait_for_selector(
            'xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div/div[1]/div/form/div[1]/div[2]/div/input',
            timeout=10000
        )
        await password_field.click()
        await password_field.type(password)
        
        # Click continue after password (exact xpath from original)
        continue_after_pwd_btn = await page.wait_for_selector(
            'xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div/div[1]/div/form/div[2]/button',
            timeout=10000
        )
        await continue_after_pwd_btn.click()
        
        await asyncio.sleep(2)
        
        # Fill TOTP (by id - same as original)
        totp_field = await page.wait_for_selector('#totp_input', timeout=10000)
        await totp_field.click()
        current_totp = _generate_totp(totp_key)
        await totp_field.type(current_totp)
        
        # Click login (exact xpath from original)
        login_btn = await page.wait_for_selector(
            'xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div/div/div/form/div[2]/button',
            timeout=10000
        )
        await login_btn.click()
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Jainam Lite login error: {e}")
        return {"status": False, "message": str(e)}


async def run_kotak_neo_login(page: Page, account: dict) -> dict:
    """
    Login to Kotak Neo broker account.
    Same as original - just navigates to cirrus.trade with credentials.
    """
    try:
        client_id = account['client_id'].strip()
        mpin = account['mpin'].strip()
        totp_key = account['totp_key'].strip()
        mobile_number = account.get('mobile_number', '').strip()
        
        totp = _generate_totp(totp_key)
        
        url = f"https://cirrus.trade/add-broker-account/kotak-neo?totp={totp}&client_id={client_id}&mpin={mpin}&mobile_number={mobile_number}"
        await page.goto(url, wait_until='domcontentloaded')
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Kotak Neo login error: {e}")
        return {"status": False, "message": str(e)}


async def run_fyers_login(page: Page, account: dict) -> dict:
    """
    Login to Fyers broker account.
    Same as original - uses API to get auth code, then navigates to cirrus.trade.
    """
    try:
        client_id = account['client_id'].strip()
        mpin = account['mpin'].strip()
        totp_key = account['totp_key'].strip()
        
        # Get auth code via API (same as original)
        auth_code = get_auto_code_fyers(
            fy_id=client_id,
            app_id=FYERS_APP_ID,
            app_type="102",
            pin=mpin,
            totp_key=totp_key,
            redirect_uri="https://app.tradinx.in/broker-login/fyers-login"
        )
        
        if not auth_code:
            return {"status": False, "message": "Failed to get auth code"}
        
        url = f"https://cirrus.trade/add-broker-account/fyers?s=ok&auth_code={auth_code}"
        await page.goto(url, wait_until='domcontentloaded')
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Fyers login error: {e}")
        return {"status": False, "message": str(e)}


async def run_fivepaisa_login(page: Page, account: dict) -> dict:
    """
    Login to 5Paisa broker account.
    Uses exact XPath selectors from original Selenium implementation.
    """
    try:
        client_id = account['client_id'].strip()
        mpin = account['mpin'].strip()
        totp_key = account['totp_key'].strip()
        
        url = f"https://dev-openapi.5paisa.com/WebVendorLogin/VLogin/Index?VendorKey=TcH8gqNZb0MknbgYJrtPRMOvztGruOc8&ResponseURL=https://cirrus.trade/add-broker-account/sso-5paisa&State={client_id}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill client ID (exact xpath from original)
        user_id_field = await page.wait_for_selector(
            'xpath=/html/body/section/div/div/div[2]/div/div[1]/div[1]/input',
            timeout=10000
        )
        await user_id_field.click()
        await user_id_field.type(client_id)
        
        await asyncio.sleep(3)
        
        # Click proceed (exact xpath from original)
        proceed_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div/div/div[2]/div/div[1]/button',
            timeout=10000
        )
        await proceed_btn.click()
        
        await asyncio.sleep(3)
        
        # Fill TOTP (6 separate fields with exact xpaths from original)
        current_totp = _generate_totp(totp_key)
        totp_xpaths = [
            '/html/body/section/div/div/div[2]/div/div[2]/div[1]/div/div/input[1]',
            '/html/body/section/div/div/div[2]/div/div[2]/div[1]/div/div/input[2]',
            '/html/body/section/div/div/div[2]/div/div[2]/div[1]/div/div/input[3]',
            '/html/body/section/div/div/div[2]/div/div[2]/div[1]/div/div/input[4]',
            '/html/body/section/div/div/div[2]/div/div[2]/div[1]/div/div/input[5]',
            '/html/body/section/div/div/div[2]/div/div[2]/div[1]/div/div/input[6]',
        ]
        
        for i, xpath in enumerate(totp_xpaths):
            field = await page.wait_for_selector(f'xpath={xpath}', timeout=10000)
            await field.click()
            await field.type(current_totp[i])
        
        await asyncio.sleep(3)
        
        # Click verify (exact xpath from original)
        verify_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div/div/div[2]/div/div[2]/button',
            timeout=10000
        )
        await verify_btn.click()
        
        await asyncio.sleep(3)
        
        # Fill PIN (6 separate fields with exact xpaths from original)
        pin_xpaths = [
            '/html/body/section/div/div/div[2]/div/div[5]/div[1]/div[1]/div/input[1]',
            '/html/body/section/div/div/div[2]/div/div[5]/div[1]/div[1]/div/input[2]',
            '/html/body/section/div/div/div[2]/div/div[5]/div[1]/div[1]/div/input[3]',
            '/html/body/section/div/div/div[2]/div/div[5]/div[1]/div[1]/div/input[4]',
            '/html/body/section/div/div/div[2]/div/div[5]/div[1]/div[1]/div/input[5]',
            '/html/body/section/div/div/div[2]/div/div[5]/div[1]/div[1]/div/input[6]',
        ]
        
        for i, xpath in enumerate(pin_xpaths):
            if i < len(mpin):
                field = await page.wait_for_selector(f'xpath={xpath}', timeout=10000)
                await field.click()
                await field.type(mpin[i])
        
        await asyncio.sleep(3)
        
        # Click submit (exact xpath from original)
        submit_btn = await page.wait_for_selector(
            'xpath=/html/body/section/div/div/div[2]/div/div[5]/div[2]/div[2]/button[2]',
            timeout=10000
        )
        await submit_btn.click()
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"5Paisa login error: {e}")
        return {"status": False, "message": str(e)}


async def run_dhan_login(page: Page, account: dict) -> dict:
    """
    Login to Dhan broker account.
    Uses flexible selectors to handle dynamic page structure.
    """
    try:
        client_id = account['client_id'].strip()
        mpin = account['mpin'].strip()
        # Remove all spaces from TOTP key to be safe
        totp_key = account['totp_key'].strip().replace(" ", "")
        mobile_no = account.get('mobile_number', '').strip()
        
        logging.info(f"Starting Dhan login for {client_id}")
        
        # Get consent ID
        consent_id = generate_dhan_consent()
        if not consent_id:
            return {"status": False, "message": "Failed to fetch consent ID"}
        
        url = f"https://auth.dhan.co/consent-login?consentId={consent_id}"
        await page.goto(url, wait_until='domcontentloaded')
        
        # Wait for page to fully load
        await asyncio.sleep(3)
        
        # Step 1: Fill mobile number
        logging.info("Dhan: Filling mobile number")
        try:
            mobile_field = await page.wait_for_selector(
                'input[type="tel"], input[type="text"][placeholder*="mobile" i], input[type="text"][placeholder*="phone" i]',
                timeout=15000
            )
        except Exception:
            # Fallback to XPath
            mobile_field = await page.wait_for_selector(
                'xpath=/html/body/app-root/div[1]/app-login/div/div[2]/div/div[2]/div[1]/div/div[2]/div/form/div[1]/input',
                timeout=10000
            )
        
        await mobile_field.click()
        await mobile_field.fill('')  # Clear first
        await mobile_field.type(mobile_no, delay=50)
        
        # Step 2: Click proceed button
        logging.info("Dhan: Clicking proceed")
        proceed_btn = await page.wait_for_selector(
            'button:has-text("Proceed"), button:has-text("Continue"), button[type="submit"]',
            timeout=10000
        )
        await proceed_btn.click()
        
        # Step 3: Wait for TOTP page and fill TOTP
        logging.info("Dhan: Waiting for TOTP page")
        await asyncio.sleep(2)
        
        # Generate TOTP
        current_otp = _generate_totp(totp_key)
        logging.info(f"Dhan: Generated TOTP (length: {len(current_otp)})")
        
        # Find TOTP inputs - look for code-input component
        totp_inputs = await page.query_selector_all('code-input input')
        if len(totp_inputs) >= 6:
            logging.info(f"Dhan: Found {len(totp_inputs)} TOTP inputs")
            # Click first input
            await totp_inputs[0].click()
            # Type TOTP digits
            for i in range(6):
                await totp_inputs[i].click()
                await totp_inputs[i].fill(current_otp[i])
                await asyncio.sleep(0.1)  # Small delay
            
            # Press Enter on the last input just in case
            await totp_inputs[-1].press("Enter")
        else:
            logging.warning(f"Dhan: Only found {len(totp_inputs)} TOTP inputs, trying XPath")
            # Fallback to exact XPath
            for i in range(6):
                xpath = f'/html/body/app-root/div[1]/app-login/div/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]/div[1]/code-input/span[{i+1}]/input'
                field = await page.wait_for_selector(f'xpath={xpath}', timeout=10000)
                await field.click()
                await field.fill(current_otp[i])
                if i == 5:
                    await field.press("Enter")

        # Step 4: Check for Proceed button (some flows have it)
        # Try waiting briefly for a button, if it appears, click it.
        try:
             totp_proceed_btn = await page.wait_for_selector(
                'button:has-text("Proceed"), button:has-text("Continue"), button[type="submit"]',
                state='visible',
                timeout=2000
             )
             if totp_proceed_btn:
                 logging.info("Dhan: Found Proceed button on TOTP page, clicking...")
                 await totp_proceed_btn.click()
        except Exception:
             pass 
        
        # Step 4: TOTP auto-submits, wait for PIN page
        logging.info("Dhan: Waiting for PIN page after TOTP submission")
        await asyncio.sleep(2)
        
        # Check for Invalid TOTP error immediately
        error_msg = await page.query_selector('text="Invalid Totp entered" >> visible=true')
        if error_msg:
             logging.error("Dhan: Invalid TOTP detected")
             return {"status": False, "message": "Invalid TOTP. Check system clock or secret key."}
        
        # Step 5: Check for PIN detection with longer timeout
        logging.info("Dhan: Waiting for PIN page (extended timeout)")
        try:
            # Wait for PIN-related text OR inputs to appear - increased timeout to 30s
            # User provided XPath indicates inputs are present even if text isn't detected
            await page.wait_for_selector(
                'text="Enter PIN" >> visible=true, text="PIN" >> visible=true, code-input input >> visible=true',
                timeout=30000
            )
            logging.info("Dhan: PIN page detected (text or inputs)")
        except Exception:
             # Check if we're back on mobile page (generic error indicator)
            mobile_visible = await page.query_selector('input[type="tel"]:visible, input[placeholder*="mobile" i]:visible')
            if mobile_visible:
                return {"status": False, "message": "TOTP verification failed - returned to mobile page"}
                
            # Check for error toast again just in case
            if await page.query_selector('text="Invalid Totp"'):
                return {"status": False, "message": "Invalid TOTP"}
            
            logging.warning("Dhan: Could not detect PIN page within timeout, attempting to continue...")
        
        # Step 5: Fill PIN
        logging.info(f"Dhan: Filling PIN (length: {len(mpin)})")
        
        # Re-query for current visible inputs (should be PIN inputs now)
        await asyncio.sleep(1)
        pin_inputs = await page.query_selector_all('code-input input')
        
        if len(pin_inputs) >= len(mpin):
            # Click first pin input
            # Click first pin input
            await pin_inputs[0].click()
            for i in range(len(mpin)):
                await pin_inputs[i].click()
                await pin_inputs[i].fill(mpin[i])
                await asyncio.sleep(0.1)
            # Press enter on last digit
            if pin_inputs:
                await pin_inputs[-1].press("Enter")
            logging.info("Dhan: PIN entered successfully")
        else:
            logging.warning(f"Dhan: Only found {len(pin_inputs)} PIN inputs, trying XPath options")
            # Fallback to exact XPath - try different structures
            pin_xpaths_options = [
                # User provided XPath (matches existing, but ensuring it's first)
                [f'/html/body/app-root/div[1]/app-login/div/div[2]/div/div[2]/div[1]/div/div[2]/div/div/div[2]/code-input/span[{i+1}]/input' for i in range(6)],
                # Alternative structure
                [f'/html/body/app-root/div[1]/app-login/div/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]/div[2]/code-input/span[{i+1}]/input' for i in range(6)],
                # Another potential variation
                [f'/html/body/app-root/div[1]/app-login/div/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]/div[1]/code-input/span[{i+1}]/input' for i in range(6)],
            ]
            
            pin_filled = False
            for pin_xpaths in pin_xpaths_options:
                try:
                    for i, xpath in enumerate(pin_xpaths):
                        if i < len(mpin):
                            field = await page.wait_for_selector(f'xpath={xpath}', timeout=5000)
                            await field.click()
                            await field.fill(mpin[i])
                            await asyncio.sleep(0.1)
                            if i == len(mpin) - 1:
                                await field.press("Enter")
                    pin_filled = True
                    break
                except Exception:
                    continue
            
            if not pin_filled:
                return {"status": False, "message": "Could not find PIN input fields"}
        
            if not pin_filled:
                return {"status": False, "message": "Could not find PIN input fields"}
        
        # Click Continue/Login button after PIN
        try:
             continue_btn = await page.wait_for_selector(
                'button:has-text("Continue"), button:has-text("Login")',
                state='visible',
                timeout=2000
             )
             if continue_btn:
                 logging.info("Dhan: Found Continue button on PIN page, clicking...")
                 await continue_btn.click()
        except Exception:
             logging.info("Dhan: Continue button not found or not needed")
        
        # Step 6: Wait for result
        logging.info("Dhan: Waiting for login result")
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved - did not reach success page"}
            
    except Exception as e:
        logging.error(f"Dhan login error: {e}")
        return {"status": False, "message": str(e)}


async def run_firstock_login(page: Page, account: dict) -> dict:
    """
    Login to Firstock broker account.
    Same as original - just navigates to cirrus.trade with credentials.
    """
    try:
        client_id = account['client_id'].strip()
        password = account['password'].strip()
        totp_key = account['totp_key'].strip()
        
        current_totp = _generate_totp(totp_key)
        
        url = f"https://cirrus.trade/add-broker-account/firstock?account_id={client_id}&totp={current_totp}&password={password}"
        await page.goto(url, wait_until='domcontentloaded')
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Firstock login error: {e}")
        return {"status": False, "message": str(e)}


async def run_pocketful_login(page: Page, account: dict) -> dict:
    """
    Login to Pocketful broker account.
    """
    try:
        client_id = account['client_id'].strip()
        password = account['password'].strip()
        
        encoded_account = client_id.encode("ascii")
        base64_account = base64.b64encode(encoded_account)
        new_client_id = base64_account.decode("ascii")
        
        url = f"https://trade.pocketful.in/oauth2/auth?scope=orders+holdings&state={new_client_id}&redirect-uri=https://cirrus.trade/add-broker-account/pocketful&response_type=code&client_id=Uadzbmlkks"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        # Fill client ID
        await page.fill('input[type="text"]', client_id)
        
        # Fill password
        await page.fill('input[type="password"]', password)
        
        # Click submit
        await page.click('button[type="submit"]')
        
        await asyncio.sleep(10)
        
        if await check_page_contains(page, "Account Saved!"):
            return {"status": True, "message": "Account Saved!"}
        else:
            return {"status": False, "message": "Account not saved"}
            
    except Exception as e:
        logging.error(f"Pocketful login error: {e}")
        return {"status": False, "message": str(e)}


# Mapping of broker names to login functions
BROKER_LOGIN_FUNCTIONS = {
    "angel_one": run_angel_one_login,
    "zerodha": run_zerodha_login,
    "upstox": run_upstox_login,
    "sharekhan": run_sharekhan_login,
    "motilal": run_motilaloswal_login,
    "nuvama": run_nuvama_login,
    "jainamlite": run_jainam_lite_login,
    "kotakneo": run_kotak_neo_login,
    "fyers": run_fyers_login,
    "fivepaisa": run_fivepaisa_login,
    "dhan": run_dhan_login,
    "firstock": run_firstock_login,
    "pocketful": run_pocketful_login,
}


async def run_broker_login(page: Page, broker: str, account: dict) -> dict:
    """
    Run login for specified broker.
    
    Args:
        page: Playwright page instance
        broker: Broker name (e.g., 'zerodha', 'angel_one')
        account: Account details dictionary
        
    Returns:
        dict with 'status' (bool) and 'message' (str)
    """
    login_func = BROKER_LOGIN_FUNCTIONS.get(broker)
    if not login_func:
        return {"status": False, "message": f"Unknown broker: {broker}"}
    
    return await login_func(page, account)
