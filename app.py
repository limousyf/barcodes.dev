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
            ip = value #.split(',')[0].strip()
            if ip:
                return ip
    
    # Fallback to remote_addr if no proxy headers found
    return request.remote_addr or 'unknown'

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
    
    def __repr__(self):
        return f'<GenerationRecord {self.code_type}: {self.code_value[:50]}>'

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

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
                user_agent=request.headers.get('User-Agent', '')
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
                user_agent=request.headers.get('User-Agent', '')
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)