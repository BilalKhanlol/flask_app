from flask import Flask, render_template, request, jsonify
import requests
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

API_URL = "https://process-image-f6be3exkra-uc.a.run.app"

def process_image(image_path=None, image_url=None):
    if image_path:
        with open(image_path, 'rb') as img:
            files = {
                'image_file': img
            }
            data = {
                'text_input': 'Write a Amazon Product Description from the Product Image'
            }
            response = requests.post(API_URL, files=files, data=data)
    else:
        json_data = {
            'image_file': image_url,
            'text_input': 'Write a Amazon Product Description from the Product Image'
        }
        response = requests.post(API_URL, json=json_data)
    
    return response.json() if response.ok else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_description():
    try:
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                result = process_image(image_path=filepath)
                os.remove(filepath)  # Clean up
                return jsonify({'description': result})
        
        elif 'image_url' in request.form:
            image_url = request.form['image_url']
            result = process_image(image_url=image_url)
            return jsonify({'description': result})
        
        return jsonify({'error': 'No image provided'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))