from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from werkzeug.security import generate_password_hash
import os
import logging
from datetime import datetime
import hashlib
import tempfile
import requests
from database import init_db, log_search, save_case_data, get_case_by_search_id, get_search_history
from scraper import DelhiHighCourtScraper, CaptchaRequiredException, ScrapingException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('court_fetcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database
init_db()

# Initialize scraper
scraper = DelhiHighCourtScraper()

@app.route('/')
def index():
    """Main search interface"""
    # Get case types from the scraper
    case_types = scraper.get_case_types()
    years = list(range(2025, 1950, -1))  # 2025 down to 1951
    return render_template('index.html', case_types=case_types, years=years)

@app.route('/search', methods=['POST'])
def search_case():
    """Handle case search submission"""
    try:
        # Get form data
        case_type = request.form.get('case_type', '').strip()
        case_number = request.form.get('case_number', '').strip()
        year = request.form.get('year', '').strip()
        captcha_code = request.form.get('captcha_code', '').strip()
        
        # Validate input
        if not all([case_type, case_number, year]):
            return render_template('index.html', 
                                 error="All fields are required",
                                 case_types=scraper.get_case_types(),
                                 years=list(range(2025, 1950, -1)))
        
        # Log the search attempt
        search_id = log_search(case_type, case_number, year)
        
        logger.info(f"Starting search for {case_type} {case_number}/{year}")
        
        # Perform the search
        try:
            case_data = scraper.search_case(
                case_type=case_type,
                case_number=case_number,
                year=year,
                captcha_code=captcha_code
            )
            
            # Save case data to database
            save_case_data(search_id, case_data)
            
            # Update search as successful
            from database import update_search_success
            update_search_success(search_id, True)
            
            logger.info(f"Successfully retrieved case data for search_id: {search_id}")
            
            return redirect(url_for('case_details', search_id=search_id))
            
        except CaptchaRequiredException as e:
            logger.warning(f"CAPTCHA required for search_id: {search_id}")
            from database import update_search_error
            update_search_error(search_id, str(e))
            
            return render_template('index.html',
                                 error="CAPTCHA verification required. Please enter the CAPTCHA code.",
                                 case_types=scraper.get_case_types(),
                                 years=list(range(2025, 1950, -1)),
                                 show_captcha=True,
                                 case_type=case_type,
                                 case_number=case_number,
                                 year=year)
        
        except ScrapingException as e:
            logger.error(f"Scraping error for search_id {search_id}: {e}")
            from database import update_search_error
            update_search_error(search_id, str(e))
            
            return render_template('index.html',
                                 error=f"Error fetching case data: {e}",
                                 case_types=scraper.get_case_types(),
                                 years=list(range(2025, 1950, -1)))
    
    except Exception as e:
        logger.error(f"Unexpected error in search_case: {e}")
        return render_template('index.html',
                             error="An unexpected error occurred. Please try again.",
                             case_types=scraper.get_case_types(),
                             years=list(range(2025, 1950, -1)))

@app.route('/case/<int:search_id>')
def case_details(search_id):
    """Display case details"""
    try:
        case_data = get_case_by_search_id(search_id)
        
        if not case_data:
            return render_template('error.html', 
                                 error="Case not found or search failed")
        
        return render_template('results.html', 
                             case_data=case_data,
                             search_id=search_id)
    
    except Exception as e:
        logger.error(f"Error displaying case details for search_id {search_id}: {e}")
        return render_template('error.html', 
                             error="Error loading case details")

@app.route('/download/<path:pdf_url>')
def download_pdf(pdf_url):
    """Download PDF files"""
    try:
        # Validate and decode the PDF URL
        pdf_url = pdf_url.replace('__SLASH__', '/')
        
        logger.info(f"Downloading PDF: {pdf_url}")
        
        # Download the PDF
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(response.content)
        temp_file.close()
        
        # Generate filename from URL
        filename = f"court_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(temp_file.name, 
                        as_attachment=True,
                        download_name=filename,
                        mimetype='application/pdf')
    
    except Exception as e:
        logger.error(f"Error downloading PDF {pdf_url}: {e}")
        return render_template('error.html', 
                             error="Error downloading PDF file")

@app.route('/api/search-history')
def api_search_history():
    """Get search history as JSON"""
    try:
        history = get_search_history(limit=50)
        return jsonify({
            'status': 'success',
            'data': history
        })
    except Exception as e:
        logger.error(f"Error fetching search history: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error fetching search history'
        }), 500

@app.route('/history')
def search_history():
    """Display search history page"""
    try:
        history = get_search_history(limit=100)
        return render_template('history.html', history=history)
    except Exception as e:
        logger.error(f"Error displaying search history: {e}")
        return render_template('error.html', 
                             error="Error loading search history")

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        from database import test_connection
        db_status = test_connection()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected' if db_status else 'disconnected',
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('error.html', 
                         error="Internal server error"), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Court Data Fetcher on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)