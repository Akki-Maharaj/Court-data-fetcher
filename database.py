import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)

DATABASE_PATH = os.getenv('DATABASE_PATH', 'court_data.db')

def get_db_connection():
    """Get database connection with proper configuration"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def init_db():
    """Initialize the database with required tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create searches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_type TEXT NOT NULL,
                case_number TEXT NOT NULL,
                year TEXT NOT NULL,
                search_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                raw_response TEXT
            )
        ''')
        
        # Create cases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                case_title TEXT,
                petitioner TEXT,
                respondent TEXT,
                filing_date DATE,
                next_hearing_date DATE,
                case_status TEXT,
                bench_info TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (search_id) REFERENCES searches (id)
            )
        ''')
        
        # Create orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                order_date DATE,
                order_type TEXT,
                pdf_url TEXT,
                pdf_downloaded BOOLEAN DEFAULT FALSE,
                order_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_searches_timestamp 
            ON searches(search_timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cases_search_id 
            ON cases(search_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_case_id 
            ON orders(case_id)
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

def log_search(case_type: str, case_number: str, year: str) -> int:
    """Log a new search attempt and return search_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO searches (case_type, case_number, year)
            VALUES (?, ?, ?)
        ''', (case_type, case_number, year))
        
        search_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"Logged search: {case_type} {case_number}/{year} (ID: {search_id})")
        return search_id
        
    except Exception as e:
        logger.error(f"Error logging search: {e}")
        raise
    finally:
        conn.close()

def update_search_success(search_id: int, success: bool, raw_response: str = None):
    """Update search success status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE searches 
            SET success = ?, raw_response = ?
            WHERE id = ?
        ''', (success, raw_response, search_id))
        
        conn.commit()
        logger.info(f"Updated search {search_id} success status: {success}")
        
    except Exception as e:
        logger.error(f"Error updating search success: {e}")
        raise
    finally:
        conn.close()

def update_search_error(search_id: int, error_message: str):
    """Update search with error message"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE searches 
            SET success = FALSE, error_message = ?
            WHERE id = ?
        ''', (error_message, search_id))
        
        conn.commit()
        logger.info(f"Updated search {search_id} with error: {error_message}")
        
    except Exception as e:
        logger.error(f"Error updating search error: {e}")
        raise
    finally:
        conn.close()

def save_case_data(search_id: int, case_data: Dict[str, Any]) -> int:
    """Save case data and return case_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert case data
        cursor.execute('''
            INSERT INTO cases (
                search_id, case_title, petitioner, respondent,
                filing_date, next_hearing_date, case_status, bench_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            search_id,
            case_data.get('case_title'),
            case_data.get('petitioner'),
            case_data.get('respondent'),
            case_data.get('filing_date'),
            case_data.get('next_hearing_date'),
            case_data.get('case_status'),
            case_data.get('bench_info')
        ))
        
        case_id = cursor.lastrowid
        
        # Insert orders/judgments
        orders = case_data.get('orders', [])
        for order in orders:
            cursor.execute('''
                INSERT INTO orders (
                    case_id, order_date, order_type, pdf_url, order_text
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                case_id,
                order.get('date'),
                order.get('type'),
                order.get('pdf_url'),
                order.get('text')
            ))
        
        conn.commit()
        logger.info(f"Saved case data for search_id {search_id}, case_id {case_id}")
        return case_id
        
    except Exception as e:
        logger.error(f"Error saving case data: {e}")
        raise
    finally:
        conn.close()

def get_case_by_search_id(search_id: int) -> Optional[Dict[str, Any]]:
    """Get case data by search_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get search info
        cursor.execute('''
            SELECT * FROM searches WHERE id = ?
        ''', (search_id,))
        search_row = cursor.fetchone()
        
        if not search_row:
            return None
        
        search_data = dict(search_row)
        
        # Get case data
        cursor.execute('''
            SELECT * FROM cases WHERE search_id = ?
        ''', (search_id,))
        case_row = cursor.fetchone()
        
        if not case_row:
            # Search exists but no case data (likely failed search)
            return {
                'search': search_data,
                'case': None,
                'orders': []
            }
        
        case_data = dict(case_row)
        
        # Get orders
        cursor.execute('''
            SELECT * FROM orders WHERE case_id = ? ORDER BY order_date DESC
        ''', (case_data['id'],))
        orders = [dict(row) for row in cursor.fetchall()]
        
        return {
            'search': search_data,
            'case': case_data,
            'orders': orders
        }
        
    except Exception as e:
        logger.error(f"Error getting case by search_id {search_id}: {e}")
        raise
    finally:
        conn.close()

def get_search_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get search history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, c.case_title 
            FROM searches s
            LEFT JOIN cases c ON s.id = c.search_id
            ORDER BY s.search_timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Error getting search history: {e}")
        raise
    finally:
        conn.close()

def get_statistics() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total searches
        cursor.execute('SELECT COUNT(*) as total FROM searches')
        total_searches = cursor.fetchone()['total']
        
        # Successful searches
        cursor.execute('SELECT COUNT(*) as total FROM searches WHERE success = TRUE')
        successful_searches = cursor.fetchone()['total']
        
        # Recent searches (last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) as total FROM searches 
            WHERE search_timestamp > datetime('now', '-1 day')
        ''')
        recent_searches = cursor.fetchone()['total']
        
        # Most searched case types
        cursor.execute('''
            SELECT case_type, COUNT(*) as count 
            FROM searches 
            GROUP BY case_type 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        popular_case_types = [dict(row) for row in cursor.fetchall()]
        
        return {
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0,
            'recent_searches': recent_searches,
            'popular_case_types': popular_case_types
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise
    finally:
        conn.close()

def test_connection() -> bool:
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def cleanup_old_data(days: int = 30):
    """Clean up old search data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete old unsuccessful searches
        cursor.execute('''
            DELETE FROM searches 
            WHERE success = FALSE 
            AND search_timestamp < datetime('now', '-' || ? || ' days')
        ''', (days,))
        
        deleted_searches = cursor.rowcount
        conn.commit()
        
        logger.info(f"Cleaned up {deleted_searches} old unsuccessful searches")
        return deleted_searches
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        raise
    finally:
        conn.close()