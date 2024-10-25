from flask import Flask, render_template, request, jsonify, send_file
import requests
import os
from werkzeug.utils import secure_filename
from PIL import Image
import io
import logging
from logging.handlers import RotatingFileHandler
import mimetypes
import re
import tempfile

app = Flask(__name__)

# Configuration
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    UPLOAD_FOLDER='temp_uploads',
    DOWNLOAD_FOLDER='downloads',
    REQUEST_TIMEOUT=300,  # 5 minutes timeout
    ALLOWED_IMAGE_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'webp'},
    ALLOWED_VIDEO_EXTENSIONS={'mp4', 'mov', 'avi', 'webm'},
    MAX_IMAGE_SIZE=(1920, 1080),  # Max resolution
    COMPRESSED_IMAGE_QUALITY=85,  # JPEG quality
    MAX_FILE_SIZE_MB=16,
    CHUNK_SIZE=8192  # Streaming chunk size
)

# Setup logging
logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

API_URL = "https://process-image-f6be3exkra-uc.a.run.app"
def extract_instagram_shortcode(url):
    """Extract the shortcode from an Instagram URL."""
    patterns = [
        r'instagram.com/p/([^/]+)',
        r'instagram.com/reel/([^/]+)',
        r'instagr.am/p/([^/]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1).split('?')[0]  # Remove any query parameters
    return None

def stream_url_to_file(url, chunk_size=8192):
    """Stream a URL to a temporary file and return the file object."""
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        
        # Stream the content
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                temp_file.write(chunk)
        
        temp_file.close()
        return temp_file.name
    except Exception as e:
        app.logger.error(f"Failed to stream file from {url}: {str(e)}")
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        return None

def get_instagram_video_info(instagram_url):
    """Get video information and download from Instagram URL."""
    try:
        shortcode = extract_instagram_shortcode(instagram_url)
        if not shortcode:
            return {'error': 'Invalid Instagram URL format'}

        api_url = "https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/get-info-rapidapi"
        headers = {
            "x-rapidapi-key": "ff814a8f8cmsh0aa30af17e3e1cdp1ed0f2jsnbd8e56c092ca",
            "x-rapidapi-host": "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com"
        }
        querystring = {"url": instagram_url}
        
        response = requests.get(api_url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            return {'error': data['error']}

        video_url = data.get('download_url')
        if not video_url:
            return {'error': 'Video URL not found'}

        # Stream video to temporary file
        temp_video_path = stream_url_to_file(video_url)
        if not temp_video_path:
            return {'error': 'Failed to download video'}

        return {
            'video_path': temp_video_path,
            'error': False,
            'hosting': 'instagram',
            'shortcode': shortcode,
            'mime_type': 'video/mp4'  # Instagram videos are typically MP4
        }

    except requests.exceptions.RequestException as e:
        app.logger.error(f"API request error: {str(e)}")
        return {'error': 'Failed to fetch Instagram data'}
    except Exception as e:
        app.logger.error(f"Error in get_instagram_video_info: {str(e)}")
        return {'error': 'An unexpected error occurred'}

def process_video(video_path):
    """Process video file and stream it to the API."""
    try:
        # Check if file exists and is a video
        if not os.path.exists(video_path):
            return {"error": "Video file not found"}

        mime_type = mimetypes.guess_type(video_path)[0]
        if not mime_type or not mime_type.startswith('video/'):
            return {"error": "Invalid video file"}

        # Stream the video file to the API
        with open(video_path, 'rb') as video_file:
            files = {'image_file': ('video.mp4', video_file, 'video/mp4')}
            data = {'text_input': 'Write a Amazon Product Description from the Video'}
            
            response = requests.post(
                API_URL,
                files=files,
                data=data,
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
    except Exception as e:
        app.logger.error(f"Error processing video: {str(e)}")
        return {"error": "Failed to process video"}
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(video_path):
                os.unlink(video_path)
        except Exception as e:
            app.logger.error(f"Error cleaning up temporary file: {str(e)}")

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
        app.logger.info("Received a request to generate a description.")
        
        if 'image_url' in request.form:
            url = request.form['image_url']
            app.logger.info(f"Processing URL: {url}")
            
            # Check if it's an Instagram URL
            if 'instagram.com' in url or 'instagr.am' in url:
                result = get_instagram_video_info(url)
                if result.get('error'):
                    return jsonify({'error': result['error']}), 400
                
                # Process the video
                video_result = process_video(result['video_path'])
                return jsonify(video_result)
            
            # Handle regular image URL
            return jsonify(process_image(image_url=url))

        
        # Process file uploads if video_url is not provided
        if 'image_file' in request.files:
            file = request.files['image_file']
            app.logger.info("Received file upload.")

            if not file or not file.filename:
                app.logger.warning("No file selected.")
                return jsonify({'error': 'No file selected'}), 400

            # Check file size
            file_size = get_file_size_mb(file)
            app.logger.info(f"Uploaded file size: {file_size:.2f} MB.")
            if file_size > app.config['MAX_FILE_SIZE_MB']:
                app.logger.warning(f"File size exceeds {app.config['MAX_FILE_SIZE_MB']}MB limit.")
                return jsonify({
                    'error': f'File size exceeds {app.config["MAX_FILE_SIZE_MB"]}MB limit'
                }), 400

            # Validate file type
            filename = secure_filename(file.filename)
            mime_type, _ = mimetypes.guess_type(file.filename)
            file.seek(0)

            if not (mime_type.startswith('image/') or mime_type.startswith('video/')):
                app.logger.warning(f"Invalid file type: {mime_type}.")
                return jsonify({'error': 'Invalid file type'}), 400

            # Process image files
            if mime_type.startswith('image/'):
                if not allowed_file(filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    app.logger.warning(f"Invalid image format: {filename}.")
                    return jsonify({'error': 'Invalid image format'}), 400
                
                app.logger.info(f"Compressing image: {filename}.")
                compressed_file = compress_image(file)
                
                # Save compressed file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                with open(filepath, 'wb') as f:
                    f.write(compressed_file.getvalue())
                app.logger.info(f"Compressed image saved to: {filepath}.")

            # Process video files
            elif mime_type.startswith('video/'):
                if not allowed_file(filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
                    app.logger.warning(f"Invalid video format: {filename}.")
                    return jsonify({'error': 'Invalid video format'}), 400
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                app.logger.info(f"Video saved to: {filepath}.")

            # Process file and clean up
            try:
                app.logger.info(f"Processing file at: {filepath}.")
                result = process_image(image_path=filepath)
                app.logger.info("File processed successfully.")
                return jsonify(result)
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    app.logger.info(f"Temporary file deleted: {filepath}.")

        elif 'image_url' in request.form:
            image_url = request.form['image_url']
            app.logger.info(f"Received image URL: {image_url}.")
            if not image_url:
                app.logger.warning("No URL provided for image.")
                return jsonify({'error': 'No URL provided'}), 400
            
            result = process_image(image_url=image_url)
            app.logger.info("Successfully processed image URL.")
            return jsonify(result)

        app.logger.warning("No image or video provided in the request.")
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