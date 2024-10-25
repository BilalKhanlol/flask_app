import os
from flask import Flask, render_template, request, jsonify, send_file
from gradio_client import Client
import tempfile

app = Flask(__name__)

# Initialize Gradio client
client = Client("black-forest-labs/FLUX.1-schnell")

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

        # Generate image using the API
        result = client.predict({
            "prompt": prompt,
            "seed": seed,
            "randomize_seed": randomize_seed,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps
        }, api_name="/infer")

        # The result[0] contains the image path
        image_path = result[0]
        new_seed = result[1]
        
        return jsonify({
            'status': 'success',
            'image_path': image_path,
            'seed': new_seed
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_file(filename, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)