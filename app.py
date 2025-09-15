from flask import Flask, render_template, request, send_file
import barcode
from barcode.writer import ImageWriter
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
    
    if not text:
        return render_template('index.html', error='Please enter text to generate barcode')
    
    try:
        # Generate Code128 barcode
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(text, writer=ImageWriter())
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        # Convert to base64 for display in HTML
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return render_template('index.html', 
                             barcode_image=img_base64, 
                             text=text)
    
    except Exception as e:
        return render_template('index.html', error=f'Error generating barcode: {str(e)}')

@app.route('/download', methods=['POST'])
def download_barcode():
    text = request.form.get('text', '')
    
    if not text:
        return render_template('index.html', error='Please enter text to generate barcode')
    
    try:
        # Generate Code128 barcode
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(text, writer=ImageWriter())
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'barcode_{text}.png',
            mimetype='image/png'
        )
    
    except Exception as e:
        return render_template('index.html', error=f'Error generating barcode: {str(e)}')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)