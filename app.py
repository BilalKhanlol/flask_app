from flask import Flask, render_template, request, jsonify
import requests
import os
from werkzeug.utils import secure_filename
from PIL import Image
import io
import magic
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# Configuration
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    UPLOAD_FOLDER='temp_uploads',
    REQUEST_TIMEOUT=300,  # 5 minutes timeout
    ALLOWED_IMAGE_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'webp'},
    ALLOWED_VIDEO_EXTENSIONS={'mp4', 'mov', 'avi', 'webm'},
    MAX_IMAGE_SIZE=(1920, 1080),  # Max resolution
    COMPRESSED_IMAGE_QUALITY=85,  # JPEG quality
    MAX_FILE_SIZE_MB=16
)

# Setup logging
logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

API_URL = "https://process-image-f6be3exkra-uc.a.run.app"

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_size_mb(file):
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)
    return size_bytes / (1024 * 1024)

def compress_image(image_file):
    try:
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background

        # Resize if larger than max size
        if img.size[0] > app.config['MAX_IMAGE_SIZE'][0] or img.size[1] > app.config['MAX_IMAGE_SIZE'][1]:
            img.thumbnail(app.config['MAX_IMAGE_SIZE'], Image.Resampling.LANCZOS)

        # Save compressed image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=app.config['COMPRESSED_IMAGE_QUALITY'], optimize=True)
        output.seek(0)
        return output

    except Exception as e:
        app.logger.error(f"Image compression error: {str(e)}")
        raise

def process_image(image_path=None, image_url=None):
    try:
        if image_path:
            with open(image_path, 'rb') as img:
                files = {
                    'image_file': img
                }
                data = {
                    'text_input': 'Write a Amazon Product Description from the Product Image'
                }
                response = requests.post(
                    API_URL,
                    files=files,
                    data=data,
                    timeout=app.config['REQUEST_TIMEOUT']
                )
        else:
            json_data = {
                'image_file': image_url,
                'text_input': 'Write a Amazon Product Description from the Product Image'
            }
            response = requests.post(
                API_URL,
                json=json_data,
                timeout=app.config['REQUEST_TIMEOUT']
            )

        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        app.logger.error("API request timed out")
        return {"error": "Request timed out. Please try again."}
    except requests.RequestException as e:
        app.logger.error(f"API request error: {str(e)}")
        return {"error": f"Error processing request: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_description():
    try:
        if 'image_file' in request.files:
            file = request.files['image_file']
            
            if not file or not file.filename:
                return jsonify({'error': 'No file selected'}), 400

            # Check file size
            file_size = get_file_size_mb(file)
            if file_size > app.config['MAX_FILE_SIZE_MB']:
                return jsonify({
                    'error': f'File size exceeds {app.config["MAX_FILE_SIZE_MB"]}MB limit'
                }), 400

            # Validate file type
            filename = secure_filename(file.filename)
            mime_type = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)

            if not (mime_type.startswith('image/') or mime_type.startswith('video/')):
                return jsonify({'error': 'Invalid file type'}), 400

            # Process image files
            if mime_type.startswith('image/'):
                if not allowed_file(filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    return jsonify({'error': 'Invalid image format'}), 400
                
                # Compress image
                compressed_file = compress_image(file)
                
                # Save compressed file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                with open(filepath, 'wb') as f:
                    f.write(compressed_file.getvalue())

            # Process video files
            elif mime_type.startswith('video/'):
                if not allowed_file(filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
                    return jsonify({'error': 'Invalid video format'}), 400
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

            # Process file and clean up
            try:
                result = process_image(image_path=filepath)
                return jsonify(result)
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

        elif 'image_url' in request.form:
            image_url = request.form['image_url']
            if not image_url:
                return jsonify({'error': 'No URL provided'}), 400
            result = process_image(image_url=image_url)
            return jsonify(result)

        return jsonify({'error': 'No image provided'}), 400

    except Exception as e:
        app.logger.error(f"Error in generate_description: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'error': f'File too large. Maximum size is {app.config["MAX_FILE_SIZE_MB"]}MB'
    }), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))