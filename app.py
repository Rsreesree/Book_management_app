from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, get_flashed_messages, send_file, session
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from pathlib import Path
#import webbrowser
#import threading

#def open_browser():
    #webbrowser.open_new("http://127.0.0.1:5000")


app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Database configuration - use environment variables for security
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'Sree@123')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'books')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {
    'pdf', 'txt', 'epub', 'mobi', 'azw', 'azw3',
    'doc', 'docx', 'rtf', 'html', 'htm', 'fb2', 'cbz', 'cbr'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload folder if it doesn't exist
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

mysql = MySQL(app)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def init_tables():
    """Create users and books tables if missing"""
    try:
        cur = mysql.connection.cursor()
        
        # Create users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        )
        """)
        
        # Create categories table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            user_id INT,
            UNIQUE KEY unique_category_per_user (name, user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        # Create books table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            author VARCHAR(100),
            link VARCHAR(500),
            file_name VARCHAR(255),
            category_id INT,
            user_id INT,
            reading_status ENUM('want_to_read', 'reading', 'finished') DEFAULT 'want_to_read',
            total_pages INT,
            current_page INT DEFAULT 0,
            start_date DATE,
            finish_date DATE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
        """)
        
        
        mysql.connection.commit()
        cur.close()
        print("✅ Tables initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing tables: {e}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_books(category_id=None):
    """Fetch all books for current user, optionally filtered by category"""
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        if category_id:
            cur.execute("""
                SELECT b.*, c.name as category_name 
                FROM books b 
                LEFT JOIN categories c ON b.category_id = c.id 
                WHERE b.user_id = %s AND b.category_id = %s 
                ORDER BY b.id
            """, (user_id, category_id))
        else:
            cur.execute("""
                SELECT b.*, c.name as category_name 
                FROM books b 
                LEFT JOIN categories c ON b.category_id = c.id 
                WHERE b.user_id = %s 
                ORDER BY b.id
            """, (user_id,))
        books = cur.fetchall()
        cur.close()
        return books
    except Exception as e:
        print(f"Error fetching books: {e}")
        return []

def get_all_categories():
    """Fetch all categories for current user"""
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        cur.execute("SELECT * FROM categories WHERE user_id = %s ORDER BY name", (user_id,))
        categories = cur.fetchall()
        cur.close()
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

def render_page(title, content):
    """Helper function to render a page with base template"""
    return render_template('base.html', title=title, content=content)

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Both username and password are required', 'error')
            return redirect('/login')
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cur.fetchone()
            cur.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f'Welcome back, {username}!', 'success')
                return redirect('/')
            else:
                flash('Invalid username or password', 'error')
                return redirect('/login')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect('/login')
    
    content = '''
    <div style="max-width: 400px; margin: 0 auto;">
        <h2 class="page-title">Login</h2>
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter password" required>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="submit" class="btn">Login</button>
                <a href="/register" class="btn btn-secondary">Register</a>
            </div>
        </form>
    </div>
    '''
    return render_template_string(render_page('Login - Book Master', content))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm', '').strip()
        
        if not username or not password or not confirm:
            flash('All fields are required', 'error')
            return redirect('/register')
        if password != confirm:
            flash('Passwords do not match', 'error')
            return redirect('/register')
        
        try:
            password_hash = generate_password_hash(password)
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s,%s)", (username, password_hash))
            mysql.connection.commit()
            cur.close()
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
        except Exception as e:
            flash(f'Error: Username may already exist.', 'error')
            return redirect('/register')
    
    content = '''
    <div style="max-width: 400px; margin: 0 auto;">
        <h2 class="page-title">Register</h2>
        <form method="post">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" placeholder="Choose a username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Enter password" required>
            </div>
            <div class="form-group">
                <label>Confirm Password</label>
                <input type="password" name="confirm" placeholder="Confirm password" required>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="submit" class="btn">Register</button>
                <a href="/login" class="btn btn-secondary">Login</a>
            </div>
        </form>
    </div>
    '''
    return render_template_string(render_page('Register - Book Master', content))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect('/login')

@app.route('/')
def index():
    content = '''
    <div style="text-align: center; padding: 40px 0;">
        <h2 style="color: #e2e8f0; font-size: 36px; margin-bottom: 20px;">Welcome to Book Master</h2>
        <p style="color: #cbd5e1; font-size: 18px; margin-bottom: 40px;">
            Organize and manage your book collection with ease
        </p>
        
        <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
            <a href="/books" class="btn">View All Books</a>
            <a href="/add_book" class="btn">Add New Book</a>
        </div>

        <div class="features-grid">
            <div class="feature-card">
                <h3>📖 Add Books</h3>
                <p>Easily add new books to your collection with title and author information.</p>
            </div>
            
            <div class="feature-card">
                <h3>✏️ Edit Books</h3>
                <p>Update book details anytime to keep your library accurate and up-to-date.</p>
            </div>
            
            <div class="feature-card">
                <h3>🔍 Search Books</h3>
                <p>Quickly find books by searching for titles or authors in your collection.</p>
            </div>
        </div>
    </div>
    '''
    return render_template_string(render_page('Home - Book Master', content))

@app.route('/books')
@login_required
def display_books():
    category_id = request.args.get('category')
    status_filter = request.args.get('status')
    books = get_all_books(category_id=category_id if category_id else None)
    categories = get_all_categories()
    search_query = request.args.get('q', '')
    
    # Apply status filter
    if status_filter:
        books = [b for b in books if b.get('reading_status') == status_filter]
    
    if search_query:
        try:
            cur = mysql.connection.cursor()
            user_id = session.get('user_id')
            query = """SELECT b.*, c.name as category_name 
                       FROM books b 
                       LEFT JOIN categories c ON b.category_id = c.id 
                       WHERE b.user_id = %s AND (b.title LIKE %s OR b.author LIKE %s)"""
            params = [user_id, f'%{search_query}%', f'%{search_query}%']
            
            if category_id:
                query += " AND b.category_id = %s"
                params.append(category_id)
            if status_filter:
                query += " AND b.reading_status = %s"
                params.append(status_filter)
            
            query += " ORDER BY b.id"
            cur.execute(query, params)
            books = cur.fetchall()
            cur.close()
        except Exception as e:
            print(f"Error searching books: {e}")
    
    # Build status filter buttons
    status_filter_html = '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;">'
    status_options = [
        ('', 'All Status', '📚'),
        ('want_to_read', 'Not started', '📖'),
        ('reading', 'Currently Reading', '📗'),
        ('finished', 'Finished', '✅')
    ]
    for val, label, icon in status_options:
        active = '' if status_filter != val else ''
        btn_class = 'btn-secondary' if status_filter != val else 'btn'
        status_filter_html += f'<a href="/books?{"category=" + category_id + "&" if category_id else ""}status={val}" class="btn {btn_class}" style="padding: 8px 16px; font-size: 14px;">{icon} {label}</a>'
    status_filter_html += '</div>'
    
    # Build category filter buttons
    category_filter = '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">'
    category_filter += f'<a href="/books?{"status=" + status_filter if status_filter else ""}" class="btn {"" if not category_id else "btn-secondary"}" style="padding: 8px 16px;">All Books</a>'
    for cat in categories:
        btn_class = "btn-secondary" if str(cat['id']) != category_id else "btn"
        category_filter += f'<a href="/books?category={cat["id"]}{"&status=" + status_filter if status_filter else ""}" class="btn {btn_class}" style="padding: 8px 16px;">{cat["name"]}</a>'
    category_filter += '</div>'
    
    books_html = ""
    if books:
        books_html = '<div style="display: grid; gap: 20px;">'
        for book in books:
            # Calculate reading progress
            progress_html = ""
            if book.get('total_pages') and book.get('total_pages') > 0:
                current = book.get('current_page', 0)
                total = book['total_pages']
                percentage = min(100, int((current / total) * 100))
                progress_html = f'''
                <div style="margin-top: 10px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">
                        <span>Progress: {current}/{total} pages</span>
                        <span>{percentage}%</span>
                    </div>
                    <div style="background: #334155; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="background: #0ea5e9; height: 100%; width: {percentage}%; transition: width 0.3s ease;"></div>
                    </div>
                </div>
                '''
            
            # Status badge
            status_badges = {
                'want_to_read': ('📖 Not started', '#6366f1'),
                'reading': ('📗 Reading', '#22c55e'),
                'finished': ('✅ Finished', '#10b981')
            }
            status = book.get('reading_status', 'want_to_read')
            status_text, status_color = status_badges.get(status, ('📚 Unknown', '#64748b'))
            status_badge = f'<span style="display: inline-block; background: {status_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-top: 5px; margin-right: 8px;">{status_text}</span>'
            
            # Dates display
            dates_html = ""
            if book.get('start_date'):
                dates_html += f'<p style="font-size: 13px; color: #94a3b8; margin-top: 5px;">Started: {book["start_date"]}</p>'
            if book.get('finish_date'):
                dates_html += f'<p style="font-size: 13px; color: #94a3b8; margin-top: 2px;">Finished: {book["finish_date"]}</p>'
            
            link_html = ""
            if book.get('link'):
                safe_link = book["link"].replace('"', '&quot;')
                link_html = f'<p style="margin-top: 8px;"><a href="{safe_link}" target="_blank" class="btn" style="padding: 8px 16px; font-size: 14px;">📖 View Book</a></p>'
            
            file_html = ""
            if book.get('file_name'):
                file_name = book['file_name']
                file_ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else 'file'
                file_icon = '📄' if file_ext == 'pdf' else '📝'
                book_id = book['id']
                file_html = f'<p style="margin-top: 8px;"><a href="/download_file/{book_id}" class="btn" style="padding: 8px 16px; font-size: 14px;">{file_icon} Download</a></p>'
            
            category_badge = ""
            if book.get('category_name'):
                category_badge = f'<span style="display: inline-block; background: #0ea5e9; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-top: 5px;">📁 {book["category_name"]}</span>'
            
            author_display = book.get('author') or 'Unknown Author'
            safe_title = book['title'].replace("'", "\\'").replace('"', '&quot;')
            safe_author = author_display.replace('"', '&quot;')
            
            books_html += f'''
            <div class="book-card">
                <div class="book-info">
                    <h3 class="book-title">{safe_title}</h3>
                    <p class="book-author">by {safe_author}</p>
                    {status_badge}
                    {category_badge}
                    <p class="book-id">ID: {book['id']}</p>
                    {dates_html}
                    {progress_html}
                    {link_html}
                    {file_html}
                </div>
                
                <div class="book-actions">
                    <a href="/update_progress/{book['id']}" class="btn" style="background: #22c55e;">📊 Progress</a>
                    <a href="/edit_book/{book['id']}" class="btn btn-secondary">Edit</a>
                    <form action="/delete_book/{book['id']}" method="post" 
                          onsubmit="return confirmDelete('{safe_title}');" 
                          style="margin: 0;">
                        <button type="submit" class="btn btn-danger">Delete</button>
                    </form>
                </div>
            </div>
            '''
        books_html += '</div>'
        books_html += f'<div class="stats">Total: {len(books)} book(s)</div>'
    else:
        if search_query:
            books_html = '''
            <div class="empty-state">
                <div class="empty-state-icon">📚</div>
                <h3>No books found</h3>
                <p>Try a different search term or browse all books.</p>
                <a href="/books" class="btn">View All Books</a>
            </div>
            '''
        else:
            books_html = '''
            <div class="empty-state">
                <div class="empty-state-icon">📚</div>
                <h3>No books in your library yet</h3>
                <p>Start building your collection by adding your first book!</p>
                <a href="/add_book" class="btn">Add Your First Book</a>
            </div>
            '''
    
    title_text = f'Search Results for "{search_query}"' if search_query else 'All Books'
    clear_button = f'<a href="/books" class="btn btn-secondary">Clear</a>' if search_query else ''
    
    content = f'''
    <div class="page-header">
        <h2 class="page-title">{title_text}</h2>
        <div class="header-actions">
            <a href="/add_book" class="btn">+ Add New Book</a>
        </div>
    </div>

    {status_filter_html}
    {category_filter}

    <form action="/books" method="get" class="search-container" style="max-width: 100%;">
        <input type="search" name="q" placeholder="Search by title or author..." 
               value="{search_query}">
        {f'<input type="hidden" name="category" value="{category_id}">' if category_id else ''}
        {f'<input type="hidden" name="status" value="{status_filter}">' if status_filter else ''}
        <button type="submit" class="btn">Search</button>
        {clear_button}
    </form>

    {books_html}
    '''
    return render_template_string(render_page('All Books - Book Master', content))

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        link = request.form.get('link', '').strip()
        category_id = request.form.get('category_id', '').strip()
        reading_status = 'want_to_read'  # Always set to not started for new books
        total_pages = request.form.get('total_pages', '').strip()
        file_name = None
        
        if not title:
            flash('Book title is required', 'error')
        else:
            try:
                if 'file' in request.files:
                    file = request.files['file']
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        import time
                        timestamp = int(time.time())
                        filename = f"{timestamp}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        file_name = filename
                
                cur = mysql.connection.cursor()
                user_id = session.get('user_id')
                cur.execute("""INSERT INTO books 
                    (title, author, link, file_name, category_id, user_id, reading_status, total_pages) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", 
                    (title, author if author else None, link if link else None, file_name, 
                     category_id if category_id else None, user_id, reading_status,
                     int(total_pages) if total_pages else None))
                mysql.connection.commit()
                cur.close()
                
                flash(f'Book "{title}" added successfully!', 'success')
                return redirect('/books')
            except Exception as e:
                flash(f'Error adding book: {str(e)}', 'error')
    
    content = get_add_book_form()
    return render_template_string(render_page('Add Book - Book Master', content))

def get_add_book_form(title='', author='', link='', category_id='', total_pages=''):
    categories = get_all_categories()
    category_options = '<option value="">No Category</option>'
    for cat in categories:
        selected = 'selected' if str(cat['id']) == str(category_id) else ''
        category_options += f'<option value="{cat["id"]}" {selected}>{cat["name"]}</option>'

    safe_title = title.replace('"', '"')
    safe_author = author.replace('"', '"')
    safe_link = link.replace('"', '"')

    return f'''
    <div style="max-width: 600px; margin: 0 auto;">
        <h2 class="page-title" style="margin-bottom: 30px;">Add New Book</h2>

        <form action="/add_book" method="post" enctype="multipart/form-data" onsubmit="return validateBookForm(event)">
            <div class="form-group">
                <label for="title">Book Title *</label>
                <input type="text" id="title" name="title" required
                       value="{safe_title}" placeholder="Enter book title" maxlength="200">
            </div>

            <div class="form-group">
                <label for="author">Author (Optional)</label>
                <input type="text" id="author" name="author"
                       value="{safe_author}" placeholder="Enter author name (or leave blank if unknown)" maxlength="100">
            </div>

            <div class="form-group">
                <label for="category_id">Category (Optional)</label>
                <select id="category_id" name="category_id" style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                    {category_options}
                </select>
                <small style="color: #94a3b8; margin-top: 5px; display: block;">
                    <a href="/categories" style="color: #0ea5e9;">Manage categories</a>
                </small>
            </div>

            <div class="form-group">
                <label for="total_pages">Total Pages (Optional)</label>
                <input type="number" id="total_pages" name="total_pages" min="1"
                       value="{total_pages}" placeholder="Enter total pages"
                       style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
            </div>

            <div class="form-group">
                <label for="link">Book Link (Optional)</label>
                <input type="text" id="link" name="link"
                       value="{safe_link}" placeholder="https://example.com/book" maxlength="500">
            </div>

            <div class="form-group">
                <label for="file">Attach File (Optional, Max 50MB)</label>
                <input type="file" id="file" name="file"
                    accept=".pdf,.txt,.epub,.mobi,.azw,.azw3,.doc,.docx,.rtf,.html,.htm,.fb2,.cbz,.cbr"
                    onchange="validateFileSize(event)">
                <small style="color: #94a3b8; margin-top: 5px; display: block;">
                    Supported: PDF, TXT, EPUB, MOBI, AZW, DOC, DOCX, RTF, HTML, FB2, CBZ, CBR
                </small>
            </div>

            <div style="display: flex; gap: 10px; margin-top: 30px;">
                <button type="submit" class="btn">Add Book</button>
                <a href="/books" class="btn btn-secondary">Cancel</a>
            </div>
        </form>
    </div>
    '''

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        link = request.form.get('link', '').strip()
        category_id = request.form.get('category_id', '').strip()
        
        if not title:
            flash('Book title is required', 'error')
            return redirect(f'/edit_book/{book_id}')
        
        try:
            cur = mysql.connection.cursor()
            user_id = session.get('user_id')
            rows = cur.execute(
                "UPDATE books SET title = %s, author = %s, link = %s, category_id = %s WHERE id = %s AND user_id = %s",
                (title, author if author else None, link if link else None, category_id if category_id else None, book_id, user_id)
            )
            mysql.connection.commit()
            cur.close()
            
            if rows > 0:
                flash('Book updated successfully!', 'success')
            else:
                flash('Book not found', 'error')
            
            return redirect('/books')
        except Exception as e:
            flash(f'Error updating book: {str(e)}', 'error')
            return redirect('/books')
    
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        cur.execute("SELECT * FROM books WHERE id = %s AND user_id = %s", (book_id, user_id))
        book = cur.fetchone()
        cur.close()
        
        if book is None:
            flash('Book not found', 'error')
            return redirect('/books')
        
        categories = get_all_categories()
        category_options = '<option value="">No Category</option>'
        for cat in categories:
            selected = 'selected' if book.get('category_id') == cat['id'] else ''
            category_options += f'<option value="{cat["id"]}" {selected}>{cat["name"]}</option>'
        
        book_link = book.get('link', '') or ''
        book_author = book.get('author', '') or ''
        safe_title = book['title'].replace('"', '&quot;')
        safe_author = book_author.replace('"', '&quot;')
        safe_link = book_link.replace('"', '&quot;')
        
        content = f'''
        <div style="max-width: 600px; margin: 0 auto;">
            <h2 class="page-title" style="margin-bottom: 30px;">Edit Book</h2>
            
            <form action="/edit_book/{book['id']}" method="post" onsubmit="return validateBookForm(event)">
                <div class="form-group">
                    <label for="title">Book Title *</label>
                    <input type="text" id="title" name="title" required 
                           value="{safe_title}" placeholder="Enter book title" maxlength="200">
                </div>
                
                <div class="form-group">
                    <label for="author">Author (Optional)</label>
                    <input type="text" id="author" name="author" 
                           value="{safe_author}" placeholder="Enter author name (or leave blank if unknown)" maxlength="100">
                </div>
                
                <div class="form-group">
                    <label for="category_id">Category (Optional)</label>
                    <select id="category_id" name="category_id" style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                        {category_options}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="link">Book Link (Optional)</label>
                    <input type="text" id="link" name="link" 
                           value="{safe_link}" placeholder="https://example.com/book" maxlength="500">
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 30px;">
                    <button type="submit" class="btn">Update Book</button>
                    <a href="/books" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
        '''
        
        return render_template_string(render_page('Edit Book - Book Master', content))
    except Exception as e:
        flash(f'Error fetching book: {str(e)}', 'error')
        return redirect('/books')

@app.route('/download_file/<int:book_id>')
@login_required
def download_file(book_id):
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        cur.execute("SELECT file_name FROM books WHERE id = %s AND user_id = %s", (book_id, user_id))
        book = cur.fetchone()
        cur.close()
        
        if not book or not book.get('file_name'):
            flash('File not found!', 'error')
            return redirect('/books')
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], book['file_name'])
        
        if not os.path.exists(file_path):
            flash('File no longer exists!', 'error')
            return redirect('/books')
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect('/books')

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        cur.execute("SELECT file_name FROM books WHERE id = %s AND user_id = %s", (book_id, user_id))
        book = cur.fetchone()
        
        rows = cur.execute("DELETE FROM books WHERE id = %s AND user_id = %s", (book_id, user_id))
        mysql.connection.commit()
        cur.close()
        
        if book and book.get('file_name'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], book['file_name'])
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as fe:
                    print(f"Warning: Could not delete file: {fe}")
        
        if rows > 0:
            flash('Book deleted successfully!', 'success')
        else:
            flash('Book not found', 'error')
    except Exception as e:
        flash(f'Error deleting book: {str(e)}', 'error')
    
    return redirect('/books')

@app.route('/categories')
@login_required
def categories():
    categories = get_all_categories()
    
    category_cards = ""
    if categories:
        for cat in categories:
            # Count books in this category
            try:
                cur = mysql.connection.cursor()
                user_id = session.get('user_id')
                cur.execute("SELECT COUNT(*) as count FROM books WHERE category_id = %s AND user_id = %s", (cat['id'], user_id))
                result = cur.fetchone()
                book_count = result['count'] if result else 0
                cur.close()
            except:
                book_count = 0
            
            safe_name = cat['name'].replace("'", "\\'").replace('"', '&quot;')
            
            category_cards += f'''
            <div class="book-card">
                <div class="book-info">
                    <h3 class="book-title">📁 {safe_name}</h3>
                    <p class="book-author">{book_count} book(s)</p>
                </div>
                <div class="book-actions">
                    <a href="/books?category={cat['id']}" class="btn btn-secondary">View Books</a>
                    <form action="/delete_category/{cat['id']}" method="post" 
                          onsubmit="return confirmDelete('{safe_name}');" style="margin: 0;">
                        <button type="submit" class="btn btn-danger">Delete</button>
                    </form>
                </div>
            </div>
            '''
    else:
        category_cards = '''
        <div class="empty-state">
            <div class="empty-state-icon">📁</div>
            <h3>No categories yet</h3>
            <p>Create your first category to organize your books!</p>
        </div>
        '''
    
    content = f'''
    <div class="page-header">
        <h2 class="page-title">Categories</h2>
    </div>
    
    <div style="max-width: 500px; margin-bottom: 30px;">
        <form action="/add_category" method="post">
            <div class="form-group" style="margin-bottom: 10px;">
                <label for="category_name">New Category Name</label>
                <input type="text" id="category_name" name="category_name" 
                       placeholder="e.g., Fiction, Science, History..." 
                       required maxlength="50">
            </div>
            <button type="submit" class="btn">+ Add Category</button>
        </form>
    </div>
    
    <div style="display: grid; gap: 20px;">
        {category_cards}
    </div>
    
    <div class="stats" style="margin-top: 30px;">
        Total: {len(categories)} categor{'y' if len(categories) == 1 else 'ies'}
    </div>
    '''
    
    return render_template_string(render_page('Categories - Book Master', content))

@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    category_name = request.form.get('category_name', '').strip()
    
    if not category_name:
        flash('Category name is required', 'error')
        return redirect('/categories')
    
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        cur.execute("INSERT INTO categories (name, user_id) VALUES (%s, %s)", (category_name, user_id))
        mysql.connection.commit()
        cur.close()
        flash(f'Category "{category_name}" added successfully!', 'success')
    except Exception as e:
        flash('Category already exists or error occurred', 'error')
    
    return redirect('/categories')

@app.route('/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        rows = cur.execute("DELETE FROM categories WHERE id = %s AND user_id = %s", (category_id, user_id))
        mysql.connection.commit()
        cur.close()
        
        if rows > 0:
            flash('Category deleted successfully!', 'success')
        else:
            flash('Category not found', 'error')
    except Exception as e:
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect('/categories')

@app.route('/update_progress/<int:book_id>', methods=['GET', 'POST'])
@login_required
def update_progress(book_id):
    if request.method == 'POST':
        reading_status = request.form.get('reading_status', '').strip()
        current_page = request.form.get('current_page', '').strip()
        total_pages = request.form.get('total_pages', '').strip()
        start_date = request.form.get('start_date', '').strip()
        finish_date = request.form.get('finish_date', '').strip()
        
        try:
            cur = mysql.connection.cursor()
            user_id = session.get('user_id')
            
            # Auto-set dates based on status
            if reading_status == 'reading' and not start_date:
                from datetime import date
                start_date = date.today()
            if reading_status == 'finished' and not finish_date:
                from datetime import date
                finish_date = date.today()
            
            cur.execute("""
                UPDATE books SET 
                reading_status = %s, 
                current_page = %s, 
                total_pages = %s,
                start_date = %s,
                finish_date = %s
                WHERE id = %s AND user_id = %s
            """, (
                reading_status,
                int(current_page) if current_page else 0,
                int(total_pages) if total_pages else None,
                start_date if start_date else None,
                finish_date if finish_date else None,
                book_id,
                user_id
            ))
            mysql.connection.commit()
            cur.close()
            
            flash('Reading progress updated!', 'success')
            return redirect('/books')
        except Exception as e:
            flash(f'Error updating progress: {str(e)}', 'error')
            return redirect(f'/update_progress/{book_id}')
    
    # GET - show form
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        cur.execute("SELECT * FROM books WHERE id = %s AND user_id = %s", (book_id, user_id))
        book = cur.fetchone()
        cur.close()
        
        if not book:
            flash('Book not found', 'error')
            return redirect('/books')
        
        safe_title = book['title'].replace('"', '&quot;')
        current_page = book.get('current_page', 0) or 0
        total_pages = book.get('total_pages', '') or ''
        reading_status = book.get('reading_status', 'want_to_read')
        start_date = book.get('start_date', '') or ''
        finish_date = book.get('finish_date', '') or ''
        
        status_options = ''
        for val, label in [('want_to_read', '📖 Not started'), ('reading', '📗 Currently Reading'), ('finished', '✅ Finished')]:
            selected = 'selected' if reading_status == val else ''
            status_options += f'<option value="{val}" {selected}>{label}</option>'
        
        content = f'''
        <div style="max-width: 600px; margin: 0 auto;">
            <h2 class="page-title" style="margin-bottom: 10px;">Update Reading Progress</h2>
            <p style="color: #94a3b8; margin-bottom: 30px;">Book: {safe_title}</p>
            
            <form action="/update_progress/{book_id}" method="post">
                <div class="form-group">
                    <label for="reading_status">Reading Status</label>
                    <select id="reading_status" name="reading_status" style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                        {status_options}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="total_pages">Total Pages</label>
                    <input type="number" id="total_pages" name="total_pages" min="1" 
                           value="{total_pages}" placeholder="Enter total pages"
                           style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                </div>
                
                <div class="form-group">
                    <label for="current_page">Current Page</label>
                    <input type="number" id="current_page" name="current_page" min="0" 
                           value="{current_page}" placeholder="Enter current page"
                           style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                </div>
                
                <div class="form-group">
                    <label for="start_date">Start Date (Optional)</label>
                    <input type="date" id="start_date" name="start_date" 
                           value="{start_date}"
                           style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                </div>
                
                <div class="form-group">
                    <label for="finish_date">Finish Date (Optional)</label>
                    <input type="date" id="finish_date" name="finish_date" 
                           value="{finish_date}"
                           style="width: 100%; padding: 12px 15px; border: 2px solid #334155; border-radius: 8px; font-size: 16px; background: #0f172a; color: #e2e8f0;">
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 30px;">
                    <button type="submit" class="btn">Update Progress</button>
                    <a href="/books" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
            
            <div style="margin-top: 30px; padding: 15px; background: #0f172a; border-radius: 8px; color: #cbd5e1; font-size: 14px; border-left: 3px solid #22c55e;">
                <strong>💡 Tip:</strong> Set total pages and current page to see a progress bar on the books page!
            </div>
        </div>
        '''
        
        return render_template_string(render_page('Update Progress - Book Master', content))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect('/books')

@app.route('/stats')
@login_required
def stats():
    try:
        cur = mysql.connection.cursor()
        user_id = session.get('user_id')
        
        # Get counts by status
        cur.execute("SELECT reading_status, COUNT(*) as count FROM books WHERE user_id = %s GROUP BY reading_status", (user_id,))
        status_counts = {row['reading_status']: row['count'] for row in cur.fetchall()}
        
        # Get total books
        cur.execute("SELECT COUNT(*) as count FROM books WHERE user_id = %s", (user_id,))
        total_books = cur.fetchone()['count']
        
        # Get recently finished books
        cur.execute("""
            SELECT title, author, finish_date 
            FROM books 
            WHERE user_id = %s AND reading_status = 'finished' AND finish_date IS NOT NULL
            ORDER BY finish_date DESC 
            LIMIT 5
        """, (user_id,))
        recent_finished = cur.fetchall()
        
        cur.close()
        
        want_to_read = status_counts.get('want_to_read', 0)
        reading = status_counts.get('reading', 0)
        finished = status_counts.get('finished', 0)
        
        recent_html = ""
        if recent_finished:
            recent_html = '<div style="margin-top: 30px;"><h3 style="color: #e2e8f0; margin-bottom: 15px;">Recently Finished</h3><div style="display: grid; gap: 15px;">'
            for book in recent_finished:
                author = book.get('author') or 'Unknown Author'
                recent_html += f'''
                <div style="background: #0f172a; padding: 15px; border-radius: 8px; border-left: 3px solid #22c55e;">
                    <div style="color: #0ea5e9; font-weight: 600;">{book["title"]}</div>
                    <div style="color: #cbd5e1; font-size: 14px;">by {author}</div>
                    <div style="color: #64748b; font-size: 13px; margin-top: 5px;">Finished: {book["finish_date"]}</div>
                </div>
                '''
            recent_html += '</div></div>'
        
        content = f'''
        <h2 class="page-title" style="margin-bottom: 30px;">📊 Reading Statistics</h2>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
            <div class="feature-card">
                <h3 style="font-size: 36px; color: #0ea5e9; margin-bottom: 5px;">{total_books}</h3>
                <p style="color: #cbd5e1;">Total Books</p>
            </div>
            
            <div class="feature-card">
                <h3 style="font-size: 36px; color: #6366f1; margin-bottom: 5px;">{want_to_read}</h3>
                <p style="color: #cbd5e1;">📖 Not started</p>
            </div>
            
            <div class="feature-card">
                <h3 style="font-size: 36px; color: #22c55e; margin-bottom: 5px;">{reading}</h3>
                <p style="color: #cbd5e1;">📗 Reading</p>
            </div>
            
            <div class="feature-card">
                <h3 style="font-size: 36px; color: #10b981; margin-bottom: 5px;">{finished}</h3>
                <p style="color: #cbd5e1;">✅ Finished</p>
            </div>
        </div>
        
        {recent_html}
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/books" class="btn">View All Books</a>
        </div>
        '''
        
        return render_template_string(render_page('Statistics - Book Master', content))
    except Exception as e:
        flash(f'Error loading stats: {str(e)}', 'error')
        return redirect('/books')

if __name__ == '__main__':
    
    with app.app_context():
        init_tables()
    
    print("\nStarting Flask server...")
    #threading.Timer(1.5, open_browser).start()
    app.run(debug=False)