import time
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import requests
import os

logger = logging.getLogger(__name__)

class CaptchaRequiredException(Exception):
    """Raised when CAPTCHA is required"""
    pass

class ScrapingException(Exception):
    """General scraping error"""
    pass

class DelhiHighCourtScraper:
    """Scraper for Delhi High Court case search"""
    
    BASE_URL = "https://delhihighcourt.nic.in/app/"
    TIMEOUT = 30
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            
            # Headless mode for production
            if os.getenv('HEADLESS_BROWSER', 'true').lower() == 'true':
                chrome_options.add_argument('--headless')
            
            # Security and performance options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')
            
            # User agent to avoid detection
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.TIMEOUT)
            
            logger.info("WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {e}")
            raise ScrapingException(f"Failed to initialize WebDriver: {e}")
    
    def get_case_types(self) -> List[str]:
        """Get available case types from the court website"""
        case_types = [
            "ADMIN.REPORT", "ARB.A.", "ARB. A. (COMM.)", "ARB.P.", "BAIL APPLN.",
            "CA", "CA (COMM.IPD-CR)", "C.A.(COMM.IPD-GI)", "C.A.(COMM.IPD-PAT)",
            "C.A.(COMM.IPD-PV)", "C.A.(COMM.IPD-TM)", "CAVEAT(CO.)", "CC(ARB.)",
            "CCP(CO.)", "CCP(REF)", "CEAC", "CEAR", "CHAT.A.C.", "CHAT.A.REF",
            "CMI", "CM(M)", "CM(M)-IPD", "C.O.", "CO.APP.", "CO.APPL.(C)",
            "CO.APPL.(M)", "CO.A(SB)", "C.O.(COMM.IPD-CR)", "C.O.(COMM.IPD-GI)",
            "C.O.(COMM.IPD-PAT)", "C.O. (COMM.IPD-TM)", "CO.EX.", "CONT.APP.(C)",
            "CONT.CAS(C)", "CONT.CAS.(CRL)", "CO.PET.", "C.REF.(O)", "CRL.A.",
            "CRL.L.P.", "CRL.M.C.", "CRL.M.(CO.)", "CRL.M.I.", "CRL.O.",
            "CRL.O.(CO.)", "CRL.REF.", "CRL.REV.P.", "CRL.REV.P.(MAT.)",
            "CRL.REV.P.(NDPS)", "CRL.REV.P.(NI)", "C.R.P.", "CRP-IPD", "C.RULE",
            "CS(COMM)", "CS(OS)", "CS(OS) GP", "CUSAA", "CUS.A.C.", "CUS.A.R.",
            "CUSTOM A.", "DEATH SENTENCE REF.", "W.P.(C)", "W.P.(C)-IPD", "W.P.(CRL)"
        ]
        return case_types
    
    def search_case(self, case_type: str, case_number: str, year: str, captcha_code: str = None) -> Dict[str, Any]:
        """Search for a case and extract details"""
        try:
            logger.info(f"Starting case search: {case_type} {case_number}/{year}")
            
            # Navigate to the search page
            self.driver.get(self.BASE_URL)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_element_located((By.NAME, "case_type"))
            )
            
            # Fill the form
            self._fill_search_form(case_type, case_number, year, captcha_code)
            
            # Submit the form
            submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()
            
            # Wait for results
            time.sleep(3)
            
            # Check if CAPTCHA error or invalid case
            if self._check_for_errors():
                raise ScrapingException("Invalid case number or CAPTCHA error")
            
            # Parse the results
            case_data = self._parse_case_results()
            
            logger.info(f"Successfully extracted case data for {case_type} {case_number}/{year}")
            return case_data
            
        except CaptchaRequiredException:
            raise
        except Exception as e:
            logger.error(f"Error in case search: {e}")
            raise ScrapingException(f"Failed to search case: {e}")
    
    def _fill_search_form(self, case_type: str, case_number: str, year: str, captcha_code: str = None):
        """Fill the search form with provided data"""
        try:
            # Select case type
            case_type_select = Select(self.driver.find_element(By.NAME, "case_type"))
            case_type_select.select_by_visible_text(case_type)
            
            # Enter case number
            case_number_input = self.driver.find_element(By.NAME, "case_number")
            case_number_input.clear()
            case_number_input.send_keys(case_number)
            
            # Select year
            year_select = Select(self.driver.find_element(By.NAME, "year"))
            year_select.select_by_visible_text(year)
            
            # Handle CAPTCHA
            if captcha_code:
                captcha_input = self.driver.find_element(By.NAME, "captcha")
                captcha_input.clear()
                captcha_input.send_keys(captcha_code)
            else:
                # Check if CAPTCHA is present
                try:
                    captcha_element = self.driver.find_element(By.NAME, "captcha")
                    if captcha_element.is_displayed():
                        raise CaptchaRequiredException("CAPTCHA verification required")
                except NoSuchElementException:
                    pass  # No CAPTCHA present
            
        except Exception as e:
            logger.error(f"Error filling search form: {e}")
            raise ScrapingException(f"Failed to fill search form: {e}")
    
    def _check_for_errors(self) -> bool:
        """Check if there are any errors in the response"""
        try:
            page_source = self.driver.page_source.lower()
            
            error_indicators = [
                "no record found",
                "invalid case number",
                "captcha mismatch",
                "error occurred",
                "try again"
            ]
            
            for indicator in error_indicators:
                if indicator in page_source:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for errors: {e}")
            return True
    
    def _parse_case_results(self) -> Dict[str, Any]:
        """Parse case results from the response page"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            case_data = {
                'case_title': None,
                'petitioner': None,
                'respondent': None,
                'filing_date': None,
                'next_hearing_date': None,
                'case_status': None,
                'bench_info': None,
                'orders': []
            }
            
            # Extract case title
            case_data['case_title'] = self._extract_case_title(soup)
            
            # Extract parties
            parties = self._extract_parties(soup)
            case_data['petitioner'] = parties.get('petitioner')
            case_data['respondent'] = parties.get('respondent')
            
            # Extract dates
            dates = self._extract_dates(soup)
            case_data['filing_date'] = dates.get('filing_date')
            case_data['next_hearing_date'] = dates.get('next_hearing_date')
            
            # Extract case status and bench info
            case_data['case_status'] = self._extract_case_status(soup)
            case_data['bench_info'] = self._extract_bench_info(soup)
            
            # Extract orders/judgments
            case_data['orders'] = self._extract_orders(soup)
            
            return case_data
            
        except Exception as e:
            logger.error(f"Error parsing case results: {e}")
            raise ScrapingException(f"Failed to parse case results: {e}")
    
    def _extract_case_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract case title from the page"""
        try:
            # Look for common patterns in case title display
            title_selectors = [
                'h2', 'h3', '.case-title', '#case-title',
                'td:contains("Case Title")', 'td:contains("Title")'
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    text = element.get_text().strip()
                    if len(text) > 10:  # Reasonable title length
                        return text
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting case title: {e}")
            return None
    
    def _extract_parties(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract petitioner and respondent information"""
        try:
            parties = {'petitioner': None, 'respondent': None}
            
            # Look for party information in tables or specific elements
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        header = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        if 'petitioner' in header and value:
                            parties['petitioner'] = value
                        elif 'respondent' in header and value:
                            parties['respondent'] = value
            
            return parties
            
        except Exception as e:
            logger.error(f"Error extracting parties: {e}")
            return {'petitioner': None, 'respondent': None}
    
    def _extract_dates(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract filing date and next hearing date"""
        try:
            dates = {'filing_date': None, 'next_hearing_date': None}
            
            # Look for date patterns in the page
            date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        header = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        if 'filing' in header or 'registration' in header:
                            date_match = re.search(date_pattern, value)
                            if date_match:
                                dates['filing_date'] = date_match.group()
                        
                        elif 'next' in header or 'hearing' in header:
                            date_match = re.search(date_pattern, value)
                            if date_match:
                                dates['next_hearing_date'] = date_match.group()
            
            return dates
            
        except Exception as e:
            logger.error(f"Error extracting dates: {e}")
            return {'filing_date': None, 'next_hearing_date': None}
    
    def _extract_case_status(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract case status"""
        try:
            # Look for status information
            status_keywords = ['status', 'stage', 'current']
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        header = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        for keyword in status_keywords:
                            if keyword in header and value:
                                return value
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting case status: {e}")
            return None
    
    def _extract_bench_info(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract bench information"""
        try:
            # Look for bench/judge information
            bench_keywords = ['bench', 'judge', 'coram', 'before']
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        header = cells[0].get_text().strip().lower()
                        value = cells[1].get_text().strip()
                        
                        for keyword in bench_keywords:
                            if keyword in header and value:
                                return value
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting bench info: {e}")
            return None
    
    def _extract_orders(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract orders and judgments with PDF links"""
        try:
            orders = []
            
            # Look for order tables
            tables = soup.find_all('table')
            
            for table in tables:
                # Check if this looks like an orders table
                headers = table.find_all('th')
                header_text = ' '.join([th.get_text().strip().lower() for th in headers])
                
                if any(keyword in header_text for keyword in ['order', 'date', 'link']):
                    rows = table.find_all('tr')[1:]  # Skip header row
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            order_data = {
                                'date': None,
                                'type': 'Order',
                                'pdf_url': None,
                                'text': None
                            }
                            
                            # Extract order date
                            date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'
                            for cell in cells:
                                date_match = re.search(date_pattern, cell.get_text())
                                if date_match:
                                    order_data['date'] = date_match.group()
                                    break
                            
                            # Extract PDF link
                            links = row.find_all('a', href=True)
                            for link in links:
                                href = link['href']
                                if '.pdf' in href.lower() or 'download' in href.lower():
                                    # Convert relative URL to absolute
                                    if href.startswith('/'):
                                        order_data['pdf_url'] = f"https://delhihighcourt.nic.in{href}"
                                    elif not href.startswith('http'):
                                        order_data['pdf_url'] = f"https://delhihighcourt.nic.in/{href}"
                                    else:
                                        order_data['pdf_url'] = href
                                    break
                            
                            # Extract order text
                            order_data['text'] = ' '.join([cell.get_text().strip() for cell in cells])
                            
                            if order_data['date'] or order_data['pdf_url']:
                                orders.append(order_data)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error extracting orders: {e}")
            return []
    
    def __del__(self):
        """Cleanup WebDriver on destruction"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")