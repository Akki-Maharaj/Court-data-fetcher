import unittest
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import modules to test
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import init_db, log_search, save_case_data, get_case_by_search_id
from scraper import DelhiHighCourtScraper, CaptchaRequiredException, ScrapingException

class TestDatabase(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()
        os.environ['DATABASE_PATH'] = self.test_db.name
        init_db()
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.test_db.name)
    
    def test_log_search(self):
        """Test logging a search"""
        search_id = log_search("W.P.(C)", "12345", "2024")
        self.assertIsInstance(search_id, int)
        self.assertGreater(search_id, 0)
    
    def test_save_and_retrieve_case_data(self):
        """Test saving and retrieving case data"""
        # Log a search first
        search_id = log_search("W.P.(C)", "12345", "2024")
        
        # Sample case data
        case_data = {
            'case_title': 'Test Case v. Test Respondent',
            'petitioner': 'Test Petitioner',
            'respondent': 'Test Respondent',
            'filing_date': '01-01-2024',
            'next_hearing_date': '15-01-2024',
            'case_status': 'Pending',
            'bench_info': 'Hon\'ble Justice Test',
            'orders': [
                {
                    'date': '01-01-2024',
                    'type': 'Order',
                    'pdf_url': 'http://example.com/order.pdf',
                    'text': 'Test order text'
                }
            ]
        }
        
        # Save case data
        case_id = save_case_data(search_id, case_data)
        self.assertIsInstance(case_id, int)
        
        # Retrieve case data
        retrieved_data = get_case_by_search_id(search_id)
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data['case']['case_title'], case_data['case_title'])
        self.assertEqual(len(retrieved_data['orders']), 1)

class TestScraper(unittest.TestCase):
    """Test scraper functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.scraper = DelhiHighCourtScraper()
    
    @patch('scraper.webdriver.Chrome')
    def test_scraper_initialization(self, mock_chrome):
        """Test scraper initialization"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        scraper = DelhiHighCourtScraper()
        self.assertIsNotNone(scraper)
    
    def test_get_case_types(self):
        """Test getting case types"""
        case_types = self.scraper.get_case_types()
        self.assertIsInstance(case_types, list)
        self.assertIn("W.P.(C)", case_types)
        self.assertIn("CRL.A.", case_types)
    
    @patch('scraper.webdriver.Chrome')
    def test_captcha_required_exception(self, mock_chrome):
        """Test CAPTCHA required exception"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Mock finding CAPTCHA element
        mock_captcha_element = Mock()
        mock_captcha_element.is_displayed.return_value = True
        mock_driver.find_element.return_value = mock_captcha_element
        
        scraper = DelhiHighCourtScraper()
        
        with self.assertRaises(CaptchaRequiredException):
            scraper._fill_search_form("W.P.(C)", "12345", "2024")

class TestFlaskApp(unittest.TestCase):
    """Test Flask application"""
    
    def setUp(self):
        """Set up test client"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()
        os.environ['DATABASE_PATH'] = self.test_db.name
        
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        with app.app_context():
            init_db()
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.test_db.name)
    
    def test_index_page(self):
        """Test index page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Court Data Fetcher', response.data)
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_search_form_validation(self):
        """Test search form validation"""
        # Test with missing data
        response = self.client.post('/search', data={
            'case_type': '',
            'case_number': '',
            'year': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'All fields are required', response.data)
    
    @patch('app.scraper.search_case')
    def test_successful_search(self, mock_search):
        """Test successful case search"""
        # Mock successful search
        mock_case_data = {
            'case_title': 'Test Case',
            'petitioner': 'Test Petitioner',
            'respondent': 'Test Respondent',
            'filing_date': '01-01-2024',
            'orders': []
        }
        mock_search.return_value = mock_case_data
        
        response = self.client.post('/search', data={
            'case_type': 'W.P.(C)',
            'case_number': '12345',
            'year': '2024'
        }, follow_redirects=False)
        
        self.assertEqual(response.status_code, 302)  # Redirect to results
    
    @patch('app.scraper.search_case')
    def test_captcha_required(self, mock_search):
        """Test CAPTCHA required scenario"""
        mock_search.side_effect = CaptchaRequiredException("CAPTCHA required")
        
        response = self.client.post('/search', data={
            'case_type': 'W.P.(C)',
            'case_number': '12345',
            'year': '2024'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CAPTCHA verification required', response.data)
    
    def test_search_history_api(self):
        """Test search history API"""
        # First, log a search
        with app.app_context():
            log_search("W.P.(C)", "12345", "2024")
        
        response = self.client.get('/api/search-history')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIsInstance(data['data'], list)

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()
        os.environ['DATABASE_PATH'] = self.test_db.name
        
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        with app.app_context():
            init_db()
    
    def tearDown(self):
        """Clean up"""
        os.unlink(self.test_db.name)
    
    def test_complete_workflow(self):
        """Test complete workflow from search to display"""
        with patch('app.scraper.search_case') as mock_search:
            # Mock case data
            mock_case_data = {
                'case_title': 'Integration Test Case',
                'petitioner': 'Test Petitioner',
                'respondent': 'Test Respondent',
                'filing_date': '01-01-2024',
                'next_hearing_date': '15-01-2024',
                'case_status': 'Pending',
                'orders': [
                    {
                        'date': '01-01-2024',
                        'type': 'Order',
                        'pdf_url': 'http://example.com/order.pdf',
                        'text': 'Test order'
                    }
                ]
            }
            mock_search.return_value = mock_case_data
            
            # Submit search
            response = self.client.post('/search', data={
                'case_type': 'W.P.(C)',
                'case_number': '12345',
                'year': '2024'
            }, follow_redirects=True)
            
            # Should show case details
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Integration Test Case', response.data)
            self.assertIn(b'Test Petitioner', response.data)

class TestErrorHandling(unittest.TestCase):
    """Test error handling"""
    
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_404_error(self):
        """Test 404 error handling"""
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)
    
    @patch('app.scraper.search_case')
    def test_scraping_exception_handling(self, mock_search):
        """Test scraping exception handling"""
        mock_search.side_effect = ScrapingException("Test scraping error")
        
        response = self.client.post('/search', data={
            'case_type': 'W.P.(C)',
            'case_number': '12345',
            'year': '2024'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error fetching case data', response.data)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_cases = [
        TestDatabase,
        TestScraper,
        TestFlaskApp,
        TestIntegration,
        TestErrorHandling
    ]
    
    for test_case in test_cases:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_case)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)