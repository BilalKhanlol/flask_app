from flask import Flask, render_template, request
import requests
import os
import base64

app = Flask(__name__)

# Endpoint of the external API
API_URL = "https://infer-f6be3exkra-uc.a.run.app/"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    prompt = request.form.get('prompt')
    seed = request.form.get('seed')
    randomize_seed = request.form.get('randomize_seed') == 'on'  # Checkbox returns 'on' if checked
    width = request.form.get('width')
    height = request.form.get('height')
    num_inference_steps = request.form.get('num_inference_steps')

    # Prepare the JSON payload for the API request
    payload = {
        "prompt": prompt,
        "seed": int(seed),
        "randomize_seed": randomize_seed,
        "width": int(width),
        "height": int(height),
        "num_inference_steps": int(num_inference_steps)
    }

    # Make the POST request to the external API
    response = requests.post(API_URL, json=payload)

    # Check if the response is OK
    if response.status_code == 200:
        # Convert the image to base64
        base64_image = base64.b64encode(response.content).decode('utf-8')
        return render_template('index.html', image_data=base64_image)

    return "Error generating image", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Use PORT env variable for Render
