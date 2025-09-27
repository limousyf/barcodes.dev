from flask import Flask, render_template, request, send_file
import barcode
from barcode.writer import ImageWriter
import qrcode
import io
import base64
from PIL import Image
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

def get_real_ip():
    """Get the real client IP address, accounting for proxies and load balancers."""
    # Check common proxy headers in order of preference
    headers_to_check = [
        'X-Forwarded-For',     # Standard header for proxies
        'X-Real-IP',           # Nginx proxy header
        'X-Forwarded',         # Older proxy header
        'Forwarded-For',       # Older proxy header
        'Forwarded'            # RFC 7239 standard
    ]
    
    for header in headers_to_check:
        value = request.headers.get(header)
        if value:
            # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
            # The first one is the original client IP
            ip = value.split(',')[0].strip()
            if ip:
                return ip
    
    # Fallback to remote_addr if no proxy headers found
    return request.remote_addr or 'unknown'

def get_debug_headers():
    """Get all request headers for debugging purposes."""
    return str(dict(request.headers)) + f" | remote_addr: {request.remote_addr}"

def log_generation_attempt(code_type, code_value, barcode_symbology=None, image_format=None, qr_options=None, success=True, error_message=None):
    """Log all generation attempts (successful and failed) to database"""
    try:
        record = GenerationRecord(
            ip_address=get_real_ip(),
            code_type=code_type,
            barcode_symbology=barcode_symbology,
            code_value=code_value,
            image_format=image_format or 'PNG',
            qr_options=qr_options,
            user_agent=request.headers.get('User-Agent', ''),
            debug_headers=get_debug_headers(),
            success=success,
            error_message=error_message
        )
        db.session.add(record)
        db.session.commit()
        print(f"✅ Logged {'successful' if success else 'failed'} {code_type} generation attempt")
    except Exception as db_error:
        print(f"❌ Database logging error: {db_error}")

# Database configuration with PostgreSQL priority and SQLite fallback
def configure_database():
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgresql://'):
        try:
            # Test PostgreSQL connection
            import psycopg2
            conn = psycopg2.connect(database_url)
            conn.close()
            print(f"✅ Connected to PostgreSQL: {database_url.split('@')[1] if '@' in database_url else 'remote'}")
            return database_url
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            print("🔄 Falling back to SQLite...")
    
    sqlite_url = 'sqlite:///barcode_records.db'
    print(f"📁 Using SQLite database: {sqlite_url}")
    return sqlite_url

app.config['SQLALCHEMY_DATABASE_URI'] = configure_database()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database model
class GenerationRecord(db.Model):
    __tablename__ = 'generation_records'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)  # Using String for SQLite compatibility
    code_type = db.Column(db.String(20), nullable=False)  # 'barcode' or 'qrcode'
    barcode_symbology = db.Column(db.String(50))  # For barcodes: 'code128', 'ean13', etc.
    code_value = db.Column(db.Text, nullable=False)
    image_format = db.Column(db.String(10), nullable=False)  # 'PNG', 'JPEG', 'WEBP'
    qr_options = db.Column(db.JSON)  # For QR codes: {fill_color, back_color, box_size, border, error_correction}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_agent = db.Column(db.Text)
    debug_headers = db.Column(db.Text)  # Temporary field for debugging
    success = db.Column(db.Boolean, nullable=False, default=True)  # True for successful generations, False for failed attempts
    error_message = db.Column(db.Text)  # Error details for failed attempts
    
    def __repr__(self):
        return f'<GenerationRecord {self.code_type}: {self.code_value[:50]}>'

# Initialize database - this will be handled by migrations in production
# For development, we'll use create_all() as a fallback
def init_db():
    """Initialize database tables"""
    try:
        db.create_all()
        print("✅ Database tables created/updated")

        # Check for missing columns and add them if needed
        columns_to_add = [
            ('debug_headers', 'TEXT', None),
            ('success', 'BOOLEAN', True),
            ('error_message', 'TEXT', None)
        ]

        # Check if we're using PostgreSQL or SQLite
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_postgresql = database_url.startswith('postgresql://')

        for column_name, column_type, default_value in columns_to_add:
            # Start each column check in a fresh transaction
            try:
                db.session.rollback()  # Ensure clean state
                db.session.execute(db.text(f"SELECT {column_name} FROM generation_records LIMIT 1")).fetchone()
                db.session.commit()
                print(f"✅ Column {column_name} already exists")
            except Exception as schema_error:
                db.session.rollback()  # Rollback failed SELECT

                if "does not exist" in str(schema_error) or f"no such column: {column_name}" in str(schema_error):
                    try:
                        print(f"🔄 Adding missing {column_name} column...")

                        if is_postgresql:
                            # PostgreSQL syntax: Add column with default value in one step
                            if default_value is not None:
                                if isinstance(default_value, bool):
                                    default_sql = 'TRUE' if default_value else 'FALSE'
                                    db.session.execute(db.text(f"ALTER TABLE generation_records ADD COLUMN {column_name} {column_type} DEFAULT {default_sql}"))
                                    # Update existing NULL values
                                    db.session.execute(db.text(f"UPDATE generation_records SET {column_name} = {default_sql} WHERE {column_name} IS NULL"))
                                else:
                                    db.session.execute(db.text(f"ALTER TABLE generation_records ADD COLUMN {column_name} {column_type} DEFAULT '{default_value}'"))
                            else:
                                db.session.execute(db.text(f"ALTER TABLE generation_records ADD COLUMN {column_name} {column_type}"))
                        else:
                            # SQLite syntax: Add column, then update if needed
                            db.session.execute(db.text(f"ALTER TABLE generation_records ADD COLUMN {column_name} {column_type}"))
                            if default_value is not None:
                                if isinstance(default_value, bool):
                                    default_sql = '1' if default_value else '0'  # SQLite boolean values
                                    db.session.execute(db.text(f"UPDATE generation_records SET {column_name} = {default_sql} WHERE {column_name} IS NULL"))
                                else:
                                    db.session.execute(db.text(f"UPDATE generation_records SET {column_name} = '{default_value}' WHERE {column_name} IS NULL"))

                        db.session.commit()
                        print(f"✅ {column_name} column added successfully")
                    except Exception as alter_error:
                        db.session.rollback()
                        print(f"❌ Failed to add {column_name} column: {alter_error}")
                        print(f"   Database type: {'PostgreSQL' if is_postgresql else 'SQLite'}")
                        print(f"   Error details: {type(alter_error).__name__}: {alter_error}")
                else:
                    print(f"⚠️  Schema check warning for {column_name}: {schema_error}")
                    db.session.rollback()  # Rollback after warning

        print("✅ Schema migration complete")

    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

with app.app_context():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug')
def debug():
    """Debug endpoint to view recent headers - updated"""
    try:
        records = GenerationRecord.query.order_by(GenerationRecord.created_at.desc()).limit(10).all()
        debug_info = []
        for record in records:
            debug_info.append({
                'ip_address': record.ip_address,
                'debug_headers': getattr(record, 'debug_headers', 'column not available'),
                'created_at': record.created_at
            })
        return str(debug_info)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/db-status')
def db_status():
    """Debug endpoint to check database status"""
    try:
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
        env_url = os.environ.get('DATABASE_URL', 'Not set')
        
        # Test basic database connection
        try:
            result = db.session.execute(db.text("SELECT 1")).fetchone()
            db_test = "✅ Database connection successful"
        except Exception as e:
            db_test = f"❌ Database connection failed: {str(e)}"
        
        # Check if all required columns exist
        columns_status = []
        required_columns = ['debug_headers', 'success', 'error_message']
        for col in required_columns:
            try:
                db.session.execute(db.text(f"SELECT {col} FROM generation_records LIMIT 1")).fetchone()
                columns_status.append(f"✅ {col} column exists")
            except Exception as e:
                columns_status.append(f"❌ {col} column missing: {str(e)}")
        
        return f"""
Database Status Report:
=====================
Environment DATABASE_URL: {env_url[:50]}...
App Database URI: {db_url[:50]}...
Connection Test: {db_test}
Schema Status:
{chr(10).join(columns_status)}
"""
    except Exception as e:
        return f"Status check error: {str(e)}"

@app.route('/migrate-schema')
def migrate_schema():
    """Manual schema migration endpoint"""
    try:
        init_db()
        return "Schema migration completed. Check /db-status for results."
    except Exception as e:
        return f"Migration error: {str(e)}"

@app.route('/generate', methods=['POST'])
def generate_barcode():
    text = request.form.get('text', '')
    barcode_type = request.form.get('barcode_type', 'code128')
    image_format = request.form.get('image_format', 'PNG')
    
    if not text:
        return render_template('index.html', error='Please enter text to generate barcode', 
                             barcode_type=barcode_type, image_format=image_format)
    
    try:
        # Get the selected barcode class with specified format
        writer = ImageWriter(format=image_format)
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_instance = barcode_class(text, writer=writer)
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        # Convert to base64 for display in HTML
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Log generation to database
        try:
            record = GenerationRecord(
                ip_address=get_real_ip(),
                code_type='barcode',
                barcode_symbology=barcode_type,
                code_value=text,
                image_format=image_format,
                user_agent=request.headers.get('User-Agent', ''),
                debug_headers=get_debug_headers()
            )
            db.session.add(record)
            db.session.commit()
        except Exception as db_error:
            # Don't fail the request if database logging fails
            print(f"Database logging error: {db_error}")
        
        return render_template('index.html', 
                             barcode_image=img_base64, 
                             text=text,
                             barcode_type=barcode_type,
                             image_format=image_format)
    
    except Exception as e:
        return render_template('index.html', 
                             error=f'Error generating {barcode_type.upper()} barcode in {image_format} format: {str(e)}', 
                             text=text,
                             barcode_type=barcode_type,
                             image_format=image_format)

@app.route('/download', methods=['POST'])
def download_barcode():
    text = request.form.get('text', '')
    barcode_type = request.form.get('barcode_type', 'code128')
    image_format = request.form.get('image_format', 'PNG')
    
    if not text:
        return render_template('index.html', error='Please enter text to generate barcode', 
                             barcode_type=barcode_type, image_format=image_format)
    
    try:
        # Get the selected barcode class with specified format
        writer = ImageWriter(format=image_format)
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_instance = barcode_class(text, writer=writer)
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        # Set the appropriate file extension and mimetype
        file_ext = image_format.lower()
        if file_ext == 'jpeg':
            file_ext = 'jpg'
        mimetype = f'image/{file_ext}'
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'{barcode_type}_barcode_{text}.{file_ext}',
            mimetype=mimetype
        )
    
    except Exception as e:
        return render_template('index.html', 
                             error=f'Error generating {barcode_type.upper()} barcode in {image_format} format: {str(e)}',
                             text=text,
                             barcode_type=barcode_type,
                             image_format=image_format)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    text = request.form.get('qr_text', '')
    error_correction = request.form.get('qr_error_correction', 'M')
    image_format = request.form.get('qr_image_format', 'PNG')
    fill_color = request.form.get('qr_fill_color', '#000000')
    back_color = request.form.get('qr_back_color', '#ffffff')
    box_size = int(request.form.get('qr_box_size', '10'))
    border = int(request.form.get('qr_border', '4'))
    
    if not text:
        return render_template('index.html', error='Please enter text to generate QR code', 
                             qr_error_correction=error_correction, qr_image_format=image_format,
                             qr_fill_color=fill_color, qr_back_color=back_color,
                             qr_box_size=box_size, qr_border=border)
    
    try:
        # Map error correction levels
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H
        }
        
        # Create QR code instance with advanced options
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=box_size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Create image with custom colors
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        # Convert to desired format
        buffer = io.BytesIO()
        if image_format == 'JPEG':
            # Convert to RGB for JPEG (remove alpha channel)
            img = img.convert('RGB')
        img.save(buffer, format=image_format)
        buffer.seek(0)
        
        # Convert to base64 for display in HTML
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Log generation to database
        try:
            qr_opts = {
                'fill_color': fill_color,
                'back_color': back_color,
                'box_size': box_size,
                'border': border,
                'error_correction': error_correction
            }
            record = GenerationRecord(
                ip_address=get_real_ip(),
                code_type='qrcode',
                code_value=text,
                image_format=image_format,
                qr_options=qr_opts,
                user_agent=request.headers.get('User-Agent', ''),
                debug_headers=get_debug_headers()
            )
            db.session.add(record)
            db.session.commit()
        except Exception as db_error:
            # Don't fail the request if database logging fails
            print(f"Database logging error: {db_error}")
        
        return render_template('index.html', 
                             qr_image=img_base64, 
                             qr_text=text,
                             qr_error_correction=error_correction,
                             qr_image_format=image_format,
                             qr_fill_color=fill_color,
                             qr_back_color=back_color,
                             qr_box_size=box_size,
                             qr_border=border)
    
    except Exception as e:
        return render_template('index.html', 
                             error=f'Error generating QR code in {image_format} format: {str(e)}', 
                             qr_text=text,
                             qr_error_correction=error_correction,
                             qr_image_format=image_format,
                             qr_fill_color=fill_color,
                             qr_back_color=back_color,
                             qr_box_size=box_size,
                             qr_border=border)

@app.route('/download_qr', methods=['POST'])
def download_qr():
    text = request.form.get('qr_text', '')
    error_correction = request.form.get('qr_error_correction', 'M')
    image_format = request.form.get('qr_image_format', 'PNG')
    fill_color = request.form.get('qr_fill_color', '#000000')
    back_color = request.form.get('qr_back_color', '#ffffff')
    box_size = int(request.form.get('qr_box_size', '10'))
    border = int(request.form.get('qr_border', '4'))
    
    if not text:
        return render_template('index.html', error='Please enter text to generate QR code', 
                             qr_error_correction=error_correction, qr_image_format=image_format,
                             qr_fill_color=fill_color, qr_back_color=back_color,
                             qr_box_size=box_size, qr_border=border)
    
    try:
        # Map error correction levels
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H
        }
        
        # Create QR code instance with advanced options
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=box_size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Create image with custom colors
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        # Convert to desired format
        buffer = io.BytesIO()
        if image_format == 'JPEG':
            # Convert to RGB for JPEG (remove alpha channel)
            img = img.convert('RGB')
        img.save(buffer, format=image_format)
        buffer.seek(0)
        
        # Set the appropriate file extension and mimetype
        file_ext = image_format.lower()
        if file_ext == 'jpeg':
            file_ext = 'jpg'
        mimetype = f'image/{file_ext}'
        
        # Create safe filename from text (limit length and remove special chars)
        safe_text = ''.join(c for c in text[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_text:
            safe_text = 'qrcode'
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'qrcode_{safe_text}.{file_ext}',
            mimetype=mimetype
        )
    
    except Exception as e:
        return render_template('index.html', 
                             error=f'Error generating QR code in {image_format} format: {str(e)}',
                             qr_text=text,
                             qr_error_correction=error_correction,
                             qr_image_format=image_format,
                             qr_fill_color=fill_color,
                             qr_back_color=back_color,
                             qr_box_size=box_size,
                             qr_border=border)

# API Endpoints for headless access
@app.route('/api/barcode', methods=['POST'])
def api_generate_barcode():
    """API endpoint for generating barcodes"""
    # Parse JSON or form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    # Extract parameters
    text = data.get('text', '').strip()
    barcode_type = data.get('barcode_type', 'code128')
    image_format = data.get('image_format', 'PNG')
    
    # Validate required parameters
    if not text:
        error_msg = 'Missing required parameter: text'
        log_generation_attempt('barcode', text or '[empty]', barcode_type, image_format, success=False, error_message=error_msg)
        return {
            'error': error_msg,
            'message': 'The text parameter is required and cannot be empty'
        }, 400
    
    # Validate barcode type
    valid_barcode_types = [
        'code128', 'code39', 'ean', 'ean13', 'ean8', 'upc', 'upca', 
        'isbn', 'isbn10', 'isbn13', 'issn', 'itf', 'gs1', 'gs1_128', 
        'codabar', 'pzn', 'jan', 'ean14', 'gtin'
    ]
    if barcode_type not in valid_barcode_types:
        error_msg = 'Invalid barcode_type'
        log_generation_attempt('barcode', text, barcode_type, image_format, success=False, error_message=f'{error_msg}: {barcode_type}')
        return {
            'error': error_msg,
            'message': f'barcode_type must be one of: {", ".join(valid_barcode_types)}',
            'provided': barcode_type
        }, 400
    
    # Validate image format
    valid_image_formats = ['PNG', 'JPEG', 'WEBP']
    if image_format.upper() not in valid_image_formats:
        error_msg = 'Invalid image_format'
        log_generation_attempt('barcode', text, barcode_type, image_format, success=False, error_message=f'{error_msg}: {image_format}')
        return {
            'error': error_msg,
            'message': f'image_format must be one of: {", ".join(valid_image_formats)}',
            'provided': image_format
        }, 400
    
    try:
        # Generate barcode
        writer = ImageWriter(format=image_format.upper())
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_instance = barcode_class(text, writer=writer)
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        # Log successful generation to database
        log_generation_attempt('barcode', text, barcode_type, image_format.upper(), success=True)
        
        # Return the image file
        file_ext = image_format.lower()
        if file_ext == 'jpeg':
            file_ext = 'jpg'
        mimetype = f'image/{file_ext}'
        
        return send_file(
            buffer,
            as_attachment=False,
            download_name=f'{barcode_type}_barcode.{file_ext}',
            mimetype=mimetype
        )
    
    except Exception as e:
        error_msg = f'Barcode generation failed: {str(e)}'
        log_generation_attempt('barcode', text, barcode_type, image_format, success=False, error_message=error_msg)
        return {
            'error': 'Barcode generation failed',
            'message': f'Error generating {barcode_type.upper()} barcode in {image_format} format: {str(e)}',
            'parameters': {
                'text': text,
                'barcode_type': barcode_type,
                'image_format': image_format
            }
        }, 500

@app.route('/api/qrcode', methods=['POST'])
def api_generate_qr():
    """API endpoint for generating QR codes"""
    # Parse JSON or form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    # Extract parameters
    text = data.get('text', '').strip()
    error_correction = data.get('error_correction', 'M')
    image_format = data.get('image_format', 'PNG')
    fill_color = data.get('fill_color', '#000000')
    back_color = data.get('back_color', '#ffffff')
    
    # Validate and parse numeric parameters
    try:
        box_size = int(data.get('box_size', '10'))
        border = int(data.get('border', '4'))
    except (ValueError, TypeError):
        error_msg = 'Invalid numeric parameter'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': data.get('box_size'), 'border': data.get('border')}
        log_generation_attempt('qrcode', text or '[empty]', None, image_format, qr_options, success=False, error_message=error_msg)
        return {
            'error': error_msg,
            'message': 'box_size and border must be valid integers'
        }, 400
    
    # Validate required parameters
    if not text:
        error_msg = 'Missing required parameter: text'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text or '[empty]', None, image_format, qr_options, success=False, error_message=error_msg)
        return {
            'error': error_msg,
            'message': 'The text parameter is required and cannot be empty'
        }, 400
    
    # Validate error correction level
    valid_error_corrections = ['L', 'M', 'Q', 'H']
    if error_correction not in valid_error_corrections:
        error_msg = 'Invalid error_correction'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=f'{error_msg}: {error_correction}')
        return {
            'error': error_msg,
            'message': f'error_correction must be one of: {", ".join(valid_error_corrections)}',
            'provided': error_correction
        }, 400
    
    # Validate image format
    valid_image_formats = ['PNG', 'JPEG', 'WEBP']
    if image_format.upper() not in valid_image_formats:
        error_msg = 'Invalid image_format'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=f'{error_msg}: {image_format}')
        return {
            'error': error_msg,
            'message': f'image_format must be one of: {", ".join(valid_image_formats)}',
            'provided': image_format
        }, 400
    
    # Validate numeric ranges
    if not (1 <= box_size <= 50):
        error_msg = 'Invalid box_size'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=f'{error_msg}: {box_size}')
        return {
            'error': error_msg,
            'message': 'box_size must be between 1 and 50',
            'provided': box_size
        }, 400
    
    if not (0 <= border <= 20):
        error_msg = 'Invalid border'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=f'{error_msg}: {border}')
        return {
            'error': error_msg,
            'message': 'border must be between 0 and 20',
            'provided': border
        }, 400
    
    # Validate color format (basic hex color validation)
    import re
    color_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
    if not color_pattern.match(fill_color):
        error_msg = 'Invalid fill_color'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=f'{error_msg}: {fill_color}')
        return {
            'error': error_msg,
            'message': 'fill_color must be a valid hex color (e.g., #000000)',
            'provided': fill_color
        }, 400
    
    if not color_pattern.match(back_color):
        error_msg = 'Invalid back_color'
        qr_options = {'error_correction': error_correction, 'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=f'{error_msg}: {back_color}')
        return {
            'error': error_msg,
            'message': 'back_color must be a valid hex color (e.g., #ffffff)',
            'provided': back_color
        }, 400
    
    try:
        # Map error correction levels
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H
        }
        
        # Create QR code instance with advanced options
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=box_size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Create image with custom colors
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        # Convert to desired format
        buffer = io.BytesIO()
        if image_format.upper() == 'JPEG':
            # Convert to RGB for JPEG (remove alpha channel)
            img = img.convert('RGB')
        img.save(buffer, format=image_format.upper())
        buffer.seek(0)
        
        # Log successful generation to database
        qr_options = {'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border, 'error_correction': error_correction}
        log_generation_attempt('qrcode', text, None, image_format.upper(), qr_options, success=True)
        
        # Return the image file
        file_ext = image_format.lower()
        if file_ext == 'jpeg':
            file_ext = 'jpg'
        mimetype = f'image/{file_ext}'
        
        return send_file(
            buffer,
            as_attachment=False,
            download_name=f'qrcode.{file_ext}',
            mimetype=mimetype
        )
    
    except Exception as e:
        error_msg = f'QR code generation failed: {str(e)}'
        qr_options = {'fill_color': fill_color, 'back_color': back_color, 'box_size': box_size, 'border': border, 'error_correction': error_correction}
        log_generation_attempt('qrcode', text, None, image_format, qr_options, success=False, error_message=error_msg)
        return {
            'error': 'QR code generation failed',
            'message': f'Error generating QR code in {image_format} format: {str(e)}',
            'parameters': {
                'text': text,
                'error_correction': error_correction,
                'image_format': image_format,
                'fill_color': fill_color,
                'back_color': back_color,
                'box_size': box_size,
                'border': border
            }
        }, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)