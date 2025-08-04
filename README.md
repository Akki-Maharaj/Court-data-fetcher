# Court Data Fetcher & Mini-Dashboard

A web application for fetching and displaying case information from the Delhi High Court website.

## 🎯 Project Overview

This application allows users to search for court cases by providing:
- **Case Type** (e.g., W.P.(C), CRL.A., etc.)
- **Case Number**
- **Filing Year**

The system then fetches case details including:
- Petitioner and Respondent information
- Filing and next hearing dates
- Case status and bench information
- Orders and judgments with PDF download links

## 🏛️ Target Court

**Delhi High Court** (https://delhihighcourt.nic.in/)

## 🚀 Features

- ✅ **Web Scraping**: Automated data extraction from court website
- ✅ **CAPTCHA Handling**: Manual CAPTCHA entry when required
- ✅ **Database Storage**: SQLite database for search history and case data
- ✅ **PDF Downloads**: Direct download of court orders and judgments
- ✅ **Search History**: Track and view past searches
- ✅ **Error Handling**: User-friendly error messages
- ✅ **Docker Support**: Containerized deployment
- ✅ **Unit Tests**: Comprehensive test coverage
- ✅ **CI/CD**: GitHub Actions workflow

## 📁 Project Structure

```
Court/
├── app.py                 # Main Flask application
├── database.py            # Database operations
├── scraper.py             # Web scraping engine
├── requirements.txt       # Python dependencies
├── dockerfile            # Docker container configuration
├── docker-compose.yml    # Multi-service deployment
├── test_scraper.py       # Unit tests
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── .github/
│   └── workflows/
│       └── ci.yml       # CI/CD pipeline
└── templates/           # HTML templates
    ├── base.html        # Base template
    ├── index.html       # Search form
    ├── results.html     # Case details
    ├── history.html     # Search history
    └── error.html       # Error pages
```

## 🛠️ Installation & Setup

### Option 1: Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Court
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Chrome browser** (required for web scraping)
   - Download from: https://www.google.com/chrome/

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open: http://localhost:5000

### Option 2: Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - Open: http://localhost:5000

## 🎮 How to Use

1. **Open the web interface** at `http://localhost:5000`

2. **Fill in the search form:**
   - **Case Type:** Select from dropdown (e.g., "W.P.(C)", "CRL.A.")
   - **Case Number:** Enter the case number
   - **Year:** Select the filing year

3. **Submit the search:**
   - If CAPTCHA appears, enter the code shown
   - Click "Search Case"

4. **View results:**
   - Case details (petitioner, respondent, dates)
   - Orders and judgments
   - PDF download links

5. **Additional features:**
   - **Search History:** View past searches at `/history`
   - **Health Check:** Monitor application status at `/health`

## 🔧 Configuration

### Environment Variables

```bash
# Flask configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development  # or production

# Database
DATABASE_PATH=court_data.db

# Browser settings
HEADLESS_BROWSER=true  # Run browser in headless mode
TIMEOUT_SECONDS=30     # Page load timeout

# Optional: Production settings
PORT=5000
```

### Database Schema

The application uses SQLite with three main tables:

1. **`searches`** - Logs all search attempts
2. **`cases`** - Stores case details
3. **`orders`** - Stores orders/judgments with PDF links

## 🧪 Testing

Run the test suite:

```bash
python test_scraper.py
```

The tests cover:
- Database operations
- Scraper functionality
- Flask application routes
- Error handling
- Integration workflows

## 🐳 Docker Configuration

### Development
```bash
docker-compose up
```

### Production
```bash
docker-compose --profile production up -d
```

Includes:
- Flask application
- PostgreSQL database (optional)
- Redis caching (optional)
- Nginx reverse proxy (optional)

## 🔒 Security & CAPTCHA Strategy

### CAPTCHA Handling
- **Manual Entry**: Users manually enter CAPTCHA codes when prompted
- **Auto-refresh**: CAPTCHA images refresh automatically every 60 seconds
- **Error Recovery**: Failed CAPTCHA attempts are logged and can be retried

### Security Measures
- **Input Validation**: All form inputs are validated
- **SQL Injection Protection**: Parameterized queries
- **XSS Protection**: Template escaping
- **Rate Limiting**: Respects court website terms

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5000/health
```

### Logs
- Application logs: `court_fetcher.log`
- Database: `court_data.db`
- Docker logs: `docker-compose logs`

## 🚨 Error Handling

The application handles various error scenarios:
- **Invalid case numbers**
- **Network timeouts**
- **CAPTCHA failures**
- **Site maintenance**
- **Database errors**

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main search interface |
| `/search` | POST | Submit case search |
| `/case/<id>` | GET | View case details |
| `/download/<url>` | GET | Download PDF files |
| `/history` | GET | Search history |
| `/api/search-history` | GET | Search history (JSON) |
| `/health` | GET | Health check |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is for educational purposes. Please respect the terms of service of the Delhi High Court website.

## ⚠️ Disclaimer

- This tool accesses publicly available court records
- Use responsibly and in accordance with court website terms
- Educational use only
- No warranty provided

## 🆘 Troubleshooting

### Common Issues

1. **Chrome/ChromeDriver not found**
   - Install Chrome browser
   - Ensure ChromeDriver is in PATH

2. **Database errors**
   - Check file permissions
   - Ensure SQLite is available

3. **Scraping failures**
   - Check internet connection
   - Verify court website is accessible
   - Try with CAPTCHA if required

4. **Docker issues**
   - Ensure Docker and Docker Compose are installed
   - Check port availability (5000)

### Support

For issues and questions:
1. Check the logs: `court_fetcher.log`
2. Run tests: `python test_scraper.py`
3. Check health: `http://localhost:5000/health` 