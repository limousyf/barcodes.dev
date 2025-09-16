from flask import Flask, render_template, request, send_file
import barcode
from barcode.writer import ImageWriter
import qrcode
import io
import base64
from PIL import Image
import os

app = Flask(__name__)

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
    
    if not text:
        return render_template('index.html', error='Please enter text to generate QR code', 
                             qr_error_correction=error_correction, qr_image_format=image_format)
    
    try:
        # Map error correction levels
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H
        }
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to desired format
        buffer = io.BytesIO()
        if image_format == 'JPEG':
            # Convert to RGB for JPEG (remove alpha channel)
            img = img.convert('RGB')
        img.save(buffer, format=image_format)
        buffer.seek(0)
        
        # Convert to base64 for display in HTML
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return render_template('index.html', 
                             qr_image=img_base64, 
                             qr_text=text,
                             qr_error_correction=error_correction,
                             qr_image_format=image_format)
    
    except Exception as e:
        return render_template('index.html', 
                             error=f'Error generating QR code in {image_format} format: {str(e)}', 
                             qr_text=text,
                             qr_error_correction=error_correction,
                             qr_image_format=image_format)

@app.route('/download_qr', methods=['POST'])
def download_qr():
    text = request.form.get('qr_text', '')
    error_correction = request.form.get('qr_error_correction', 'M')
    image_format = request.form.get('qr_image_format', 'PNG')
    
    if not text:
        return render_template('index.html', error='Please enter text to generate QR code', 
                             qr_error_correction=error_correction, qr_image_format=image_format)
    
    try:
        # Map error correction levels
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H
        }
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
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
                             qr_image_format=image_format)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)