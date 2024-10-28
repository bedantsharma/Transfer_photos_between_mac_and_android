import os
import uuid
import time
import socket
import qrcode
import threading
import webbrowser
from PIL import Image
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit per image

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the original extension."""
    ext = os.path.splitext(original_filename)[1].lower()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"img_{timestamp}_{unique_id}{ext}"

def get_local_ip():
    """Get local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        s.close()
        return IP
    except Exception:
        return '127.0.0.1'

def generate_qr_code(url):
    """Generate QR code and save it as an image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create QR code image in RGB mode
    qr_image = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Get the size of the QR code image
    qr_width, qr_height = qr_image.size
    
    # Create a new image with padding for text
    padding = 60  # Padding for text
    final_image = Image.new('RGB', 
                           (qr_width, qr_height + padding), 
                           'white')
    
    # Paste QR code into the new image
    final_image.paste(qr_image, (0, 0))
    
    # Save the image
    qr_file_path = 'qr_code.png'
    final_image.save(qr_file_path)
    return qr_file_path

def create_html_page(url, qr_image_path):
    """Create an HTML page to display the QR code and URL."""
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Page QR Code</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f5f5f7;
            }}
            .container {{
                background-color: white;
                padding: 2rem;
                border-radius: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
                width: 90%;
            }}
            h2 {{
                color: #1d1d1f;
                margin-bottom: 1.5rem;
            }}
            .qr-code {{
                margin: 1.5rem 0;
            }}
            .qr-code img {{
                max-width: 100%;
                height: auto;
            }}
            .url {{
                word-break: break-all;
                margin: 1rem 0;
                padding: 0.75rem;
                background-color: #f5f5f7;
                border-radius: 8px;
                font-family: monospace;
            }}
            .copy-button {{
                background-color: #0071e3;
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1rem;
                transition: background-color 0.2s;
            }}
            .copy-button:hover {{
                background-color: #0077ed;
            }}
            .status {{
                margin-top: 1rem;
                color: #00b300;
                min-height: 1.5rem;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Scan QR Code to Access Upload Page</h2>
            <div class="qr-code">
                <img src="{qr_image_path}" alt="QR Code">
            </div>
            <div class="url">{url}</div>
            <button class="copy-button" onclick="copyUrl()">Copy URL</button>
            <div class="status" id="status"></div>
        </div>

        <script>
            function copyUrl() {{
                navigator.clipboard.writeText('{url}').then(function() {{
                    document.getElementById('status').textContent = 'URL copied to clipboard!';
                    setTimeout(() => {{
                        document.getElementById('status').textContent = '';
                    }}, 2000);
                }});
            }}
        </script>
    </body>
    </html>
    '''
    
    html_file_path = 'qr_page.html'
    with open(html_file_path, 'w') as f:
        f.write(html_content)
    return html_file_path

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'images' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('images')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected files'}), 400
    
    uploaded_files = []
    failed_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            try:
                unique_filename = generate_unique_filename(secure_filename(file.filename))
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                uploaded_files.append({
                    'original_name': file.filename,
                    'saved_as': unique_filename
                })
            except Exception as e:
                failed_files.append({
                    'filename': file.filename,
                    'error': str(e)
                })
                print(f"Error uploading {file.filename}: {str(e)}")
    
    if not uploaded_files:
        return jsonify({
            'error': 'No valid files were uploaded',
            'failed_files': failed_files
        }), 400
    
    return jsonify({
        'message': f'Successfully uploaded {len(uploaded_files)} files',
        'uploaded_files': uploaded_files,
        'failed_files': failed_files
    }), 200

def open_browser(html_file_path):
    """Open the QR code page in the default browser."""
    webbrowser.open('file://' + os.path.abspath(html_file_path))

if __name__ == '__main__':
    port = 5000
    ip = get_local_ip()
    url = f'http://{ip}:{port}'
    
    # Generate QR code and create HTML page
    qr_image_path = generate_qr_code(url)
    html_file_path = create_html_page(url, qr_image_path)
    
    # Open QR code page in browser
    threading.Timer(1.5, open_browser, args=[html_file_path]).start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)