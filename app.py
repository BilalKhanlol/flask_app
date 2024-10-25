from flask import Flask, render_template, request, send_file
import requests
import os

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
    # Make the POST request to the external API
    response = requests.post(API_URL, json=payload)

    # Check if the response is OK
    if response.status_code == 200:
        # Save the image to a file
        output_file = os.path.join(IMAGE_DIR, 'output_image.webp')
        with open(output_file, 'wb') as f:
            f.write(response.content)

        # Return the image path for displaying in the HTML
        return render_template('index.html', image_path='images/output_image.webp')

    return "Error generating image", 500

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))  # Use PORT env variable for Render