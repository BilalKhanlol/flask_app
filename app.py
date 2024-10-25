import os
from flask import Flask, render_template, request, jsonify, send_file
from gradio_client import Client
import tempfile
# from dotenv import load_dotenv
import logging

# Load environment variables from .env file
# load_dotenv()
API_KEY="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"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Also log to the console
    ]
)

app = Flask(__name__)

# Initialize Gradio client
client = Client("black-forest-labs/FLUX.1-schnell", api_key=API_KEY)


# Create a temporary directory to store generated images
TEMP_DIR = tempfile.mkdtemp()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    try:
        # Get parameters from request
        data = request.json
        prompt = data.get('prompt', '')
        seed = float(data.get('seed', 0))
        randomize_seed = data.get('randomize_seed', True)
        width = float(data.get('width', 1024))
        height = float(data.get('height', 1024))
        num_inference_steps = float(data.get('num_inference_steps', 4))

        # Log received data
        logging.debug(f"Received data: {data}")
        logging.debug(f"Prompt: {prompt}")

        # Generate image using the API
        result = client.predict(
            prompt,  # The prompt as a single argument
            seed,
            randomize_seed,
            width,
            height,
            num_inference_steps)
        # The result[0] contains the image path
        image_path = result[0]
        new_seed = result[1]
        
        return jsonify({
            'status': 'success',
            'image_path': image_path,
            'seed': new_seed
        })

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")  # Log the error
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while generating the image.',
            'details': str(e)  # Include error details if necessary
        }), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_file(filename, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
