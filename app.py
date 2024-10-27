from flask import Flask, render_template, request, jsonify, send_file ,send_from_directory
import requests
import os
from werkzeug.utils import secure_filename
from PIL import Image
import io
import logging
from logging.handlers import RotatingFileHandler
import mimetypes
import re
import shutil
import tempfile

app = Flask(__name__)

# Configuration
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    UPLOAD_FOLDER='temp_uploads',
    DOWNLOAD_FOLDER='downloads',
    TEMP_VIDEO_DIR='tmp',
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
def extract_shortcode(url):
    """Extract the shortcode or unique identifier from various platform URLs."""
    
    # Define patterns for each supported platform
    patterns = {
        'instagram': [
            r'instagram.com/p/([^/]+)',
            r'instagram.com/reel/([^/]+)',
            r'instagr.am/p/([^/]+)'
        ],
        'tiktok': [
            r'tiktok.com/@[^/]+/video/([^?&/]+)'
        ],
        'capcut': [
            r'capcut.com/share/([^/]+)'
        ],
        'pinterest': [
            r'pinterest.com/pin/([^/]+)'
        ],
        'imdb': [
            r'imdb.com/title/([^/]+)'
        ],
        'imgur': [
            r'imgur.com/(?:gallery/|a/)?([^/]+)'
        ],
        'ifunny': [
            r'ifunny.co/video/([^/]+)',
            r'ifunny.co/picture/([^/]+)'
        ],
        'reddit': [
            r'reddit.com/r/[^/]+/comments/([^/]+)'
        ],
        'vimeo': [
            r'vimeo.com/(\d+)'
        ],
        'snapchat': [
            r'snapchat.com/add/([^/]+)',
            r'story.snapchat.com/s/([^/]+)'
        ],
        'likee': [
            r'likee.video/video/([^/]+)'
        ],
        'linkedin': [
            r'linkedin.com/posts/([^/]+)'
        ],
        'tumblr': [
            r'tumblr.com/post/([^/]+)'
        ],
        'hipi': [
            r'hipi.co.in/video/([^/]+)'
        ],
        'telegram': [
            r't.me/([^/]+)'
        ],
        'getstickerpack': [
            r'getstickerpack.com/stickers/([^/]+)'
        ],
        'oke.ru': [
            r'ok.ru/video/([^/]+)'
        ],
        'streamable': [
            r'streamable.com/([^/]+)'
        ],
        'weibo': [
            r'weibo.com/(\d+)'
        ],
        'soundcloud': [
            r'soundcloud.com/[^/]+/([^/]+)'
        ],
        'mixcloud': [
            r'mixcloud.com/[^/]+/([^/]+)'
        ],
        'spotify': [
            r'spotify.com/track/([^/]+)',
            r'open.spotify.com/track/([^/]+)'
        ],
        'zingmp3': [
            r'zingmp3.vn/bai-hat/([^/]+)'
        ]
    }

    # Iterate over the patterns dictionary to find a match for the URL
    for platform, regex_patterns in patterns.items():
        for pattern in regex_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1).split('?')[0]  # Remove any query parameters

    # Return None if no patterns match
    return None
def stream_url_to_file(url, chunk_size=8192):
    """Stream a URL to a temporary file and return the file object."""
    temp_file = None  # Initialize temp_file to None for safety
    try:
        app.logger.info(f"Function: stream_url_to_file, Video URL: {url}")
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        app.logger.info("Temporary file created.")

        # Stream the content
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        app.logger.info("Successfully received response from the URL.")

        for chunk_index, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
            if chunk:
                temp_file.write(chunk)
                app.logger.debug(f"Written chunk {chunk_index} of size {len(chunk)} bytes.")

        temp_file.close()
        app.logger.info(f"Streaming completed. File saved to: {temp_file.name}")
        return temp_file.name
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request error while streaming file from {url}: {str(e)}")
    except Exception as e:
        app.logger.error(f"Failed to stream file from {url}: {str(e)}")
    # finally:
    #     if temp_file and os.path.exists(temp_file.name):
    #         app.logger.info(f"Cleaning up temporary file: {temp_file.name}")
    #         os.unlink(temp_file.name)
    
    # return None

def get_video_info(instagram_url):
    """Get video information and download from Instagram URL."""
    try:
        shortcode = extract_shortcode(instagram_url)
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

        # Log the data received from the API
        app.logger.info(f"Data received from API: {data}")

        if data.get('error'):
            app.logger.warning(f"API returned an error: {data['error']}")
            return {'error': data['error']}

        # Correctly extract the download_url from the response
        video_url = data.get('download_url')
        if not video_url:
            app.logger.warning("Video URL not found in API response.")
            return {'error': 'Video URL not found'}

        # Stream video to temporary file
        temp_video_path = stream_url_to_file(video_url)
        if not temp_video_path:
            return {'error': 'Failed to download video'}

        return {
            'video_path': temp_video_path,
            'error': False,
            'hosting': data['hosting'],  # Store hosting from the response
            'shortcode': data['shortcode'],  # Store shortcode from the response
            'caption': data.get('caption', ''),  # Optional: Store caption if needed
            'mime_type': 'video/mp4'  # Instagram videos are typically MP4
        }

    except requests.exceptions.RequestException as e:
        app.logger.error(f"API request error: {str(e)}")
        return {'error': 'Failed to fetch Instagram data'}
    except Exception as e:
        app.logger.error(f"Error in get_video_info: {str(e)}")
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

        # Define static directory path and create it if it doesn’t exist
        static_videos_path = os.path.join(app.root_path, 'static', 'videos')
        os.makedirs(static_videos_path, exist_ok=True)

        # Copy the video to the static directory for frontend access
        final_video_path = os.path.join(static_videos_path, os.path.basename(video_path))
        shutil.copy(video_path, final_video_path)

        # Stream the video file to the API
        with open(video_path, 'rb') as video_file:
            files = {'image_file': ('video.mp4', video_file, 'video/mp4')}
            data = {'text_input': 'Write an Amazon Product Description from the Video'}
            
            response = requests.post(
                API_URL,
                files=files,
                data=data,
                timeout=app.config['REQUEST_TIMEOUT']
            )

        

        # Check for successful response
        response.raise_for_status()
        result = response.json()

        app.logger.info(f" processed video: {result}")

        # Structure the output as specified
        return {
            "description": result,
            "media_url": f"/static/videos/{os.path.basename(video_path)}",
            "media_type": "video",
            "thumb": f"{request.host_url}static/videos/{os.path.basename(video_path)}"

        }

    except requests.RequestException as e:
        app.logger.error(f"Error processing video: {e}")
        return {"error": str(e)}


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
        # Initialize the request variables
        files = None
        json_data = None

        if image_path:
            with open(image_path, 'rb') as img:
                files = {
                    'image_file': img
                }
                data = {
                    'text_input': 'Write an Amazon Product Description from the Product Image'
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
                'text_input': 'Write an Amazon Product Description from the Product Image'
            }
            response = requests.post(
                API_URL,
                json=json_data,
                timeout=app.config['REQUEST_TIMEOUT']
            )

        # Check for successful response
        response.raise_for_status()
        result = response.json()

        app.logger.info(f" processed image: {result}")

        # Structure the output as specified
        return {
            "description": result,
            # "media_url": image_url if image_url else f"/images/{os.path.basename(image_path)}",
            "media_type": "image"
        }

    except requests.RequestException as e:
        app.logger.error(f"Error processing image: {e}")
        return {"error": str(e)}


@app.route('/')
def index():
    return render_template('index.html')

# New route to serve the video file
@app.route('/videos/<filename>')
def get_video(filename):
    return send_from_directory("tmp", filename)

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(TEMP_VIDEO_DIR, filename)

@app.route('/generate', methods=['POST'])
def generate_description():
    if 'test' in request.form:
        md="""# [TV Enhancer Pro: Colorful & Immersive Light Strip]
    ## Product Description
    TV Enhancer Pro is a must-have accessory for any TV owner who wants to take their viewing experience to the next level. This innovative light strip adds a splash of color and ambiance to any room, making your home entertainment setup more engaging and immersive.
    ## Key Features
    - **Easy to Install:** Simply stick the light strip to the back of your TV and plug it in. No complicated installation process or wiring required.
    - **Multiple Color Options:** Choose from a variety of colors and effects to match your mood or the content you're watching.
    - **Enhanced Viewing:** The light strip illuminates the room, reducing eye strain and creating a more immersive viewing experience.
    - **Sleek and Stylish:** The light strip is thin and discreet, so it won't detract from the look of your TV.
    ## Technical Specifications
    | Specification | Detail |
    |--------------|---------|
    | Color Modes | RGB, Warm White, Cool White, Flashing, Static |
    | Power Consumption | 5W |
    | Dimensions | 60 inches (152.4 cm) x 1 inch (2.5 cm) |
    | Material | High-quality, flexible PVC |
    | Weight | 12 oz (340 g) |
    ## What's in the Box
    - 1 x TV Enhancer Pro Light Strip
    - 1 x Adhesive Strip
    - 1 x AC Power Adapter
    - 1 x User Manual
    ## Frequently Asked Questions
    **Q: Can I install the TV Enhancer Pro light strip on a curved TV?**
    A: Yes, the flexible design of the light strip allows it to be installed on curved TVs as well as flat-screen TVs.
    **Q: Is the TV Enhancer Pro light strip waterproof?**
    A: No, the light strip is not waterproof and should not be used in areas where it may come into contact with water.
    **Q: Can I control the color and brightness of the TV Enhancer Pro light strip?**
    A: The TV Enhancer"""
        return {
            "description": md,
            "media_url": "https://scontent.cdninstagram.com/o1/v/t16/f1/m86/7345941457FBCEEC76BBA19729EB6C8D_video_dashinit.mp4?stp=dst-mp4&efg=eyJxZV9ncm91cHMiOiJbXCJpZ193ZWJfZGVsaXZlcnlfdnRzX290ZlwiXSIsInZlbmNvZGVfdGFnIjoidnRzX3ZvZF91cmxnZW4uY2xpcHMuYzIuNTc2LmJhc2VsaW5lIn0&_nc_cat=111&vs=469334266253709_1508030372&_nc_vs=HBksFQIYUmlnX3hwdl9yZWVsc19wZXJtYW5lbnRfc3JfcHJvZC83MzQ1OTQxNDU3RkJDRUVDNzZCQkExOTcyOUVCNkM4RF92aWRlb19kYXNoaW5pdC5tcDQVAALIAQAVAhg6cGFzc3Rocm91Z2hfZXZlcnN0b3JlL0dLaklmQnQwencxY1ZTTURBRkZvbWxyS3BhcEpicV9FQUFBRhUCAsgBACgAGAAbABUAACaW1IClvuKzPxUCKAJDMywXQCQQ5WBBiTcYEmRhc2hfYmFzZWxpbmVfMV92MREAdf4HAA%3D%3D&ccb=9-4&oh=00_AYC_OU8SYNlEugwxOJHdcIipZolWoYzjEGZkaaVlr0YDvg&oe=671F7663&_nc_sid=10d13b",
            "media_type": "video",
            "thumb": "https://scontent.cdninstagram.com/v/t51.29350-15/461272960_2287718244961095_6048631964334109642_n.jpg?stp=dst-jpg_e15&_nc_ht=scontent.cdninstagram.com&_nc_cat=103&_nc_ohc=jwI3NDylimkQ7kNvgFqJw1m&_nc_gid=8d40dba45b344c8ea69598d9a84fd499&edm=APs17CUBAAAA&ccb=7-5&oh=00_AYCbbJeFBOxIek4K_uKCzk3mp4qX3SE4-_FF-zdhZo1VgA&oe=67236F27&_nc_sid=10d13b"
        }
    try:
        app.logger.info("Received a request to generate a description.")
        
        if 'image_url' in request.form:
            url = request.form['image_url']
            app.logger.info(f"Processing URL: {url}")
            
            # Define supported platforms
            supported_platforms = [
                'instagram.com', 'instagr.am', 'tiktok.com', 'capcut.com',
                'pinterest.com', 'imdb.com', 'imgur.com', 'ifunny.co',
                'reddit.com', 'vimeo.com', 'snapchat.com', 'likee.video',
                'linkedin.com', 'tumblr.com', 'hipi.co.in', 't.me',
                'getstickerpack.com', 'ok.ru', 'streamable.com', 'weibo.com',
                'soundcloud.com', 'mixcloud.com', 'spotify.com', 'zingmp3.vn'
            ]

            # Check if the URL matches any supported platform
            if any(platform in url for platform in supported_platforms):
                # Process the URL with get_video_info (generalized for all platforms)
                result = get_video_info(url)
                if result.get('error'):
                    return jsonify({'error': result['error']}), 400

                # Log the entire result for debugging
                app.logger.info(f"API result for URL {url}: {result}")

                # Ensure 'video_path' exists in the result before accessing it
                if 'video_path' not in result:
                    return jsonify({'error': 'Video path not found in result'}), 400
                
                # Process the video
                video_result = process_video(result['video_path'])
                # if os.path.exists(result['video_path']):
                #     app.logger.info(f"Cleaning up temporary file: {result['video_path']}")
                #     os.unlink(result['video_path'])
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