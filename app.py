from flask import Flask, request, jsonify
from gradio_client import Client

app = Flask(__name__)
client = Client("black-forest-labs/FLUX.1-schnell")

@app.route('/infer', methods=['POST'])
def infer():
    # Get parameters from the request
    data = request.json

    prompt = data.get("prompt")
    seed = data.get("seed", 0)
    randomize_seed = data.get("randomize_seed", True)
    width = data.get("width", 1024)
    height = data.get("height", 1024)
    num_inference_steps = data.get("num_inference_steps", 4)

    # Call the Gradio client predict method
    result = client.predict(
        prompt=prompt,
        seed=seed,
        randomize_seed=randomize_seed,
        width=width,
        height=height,
        num_inference_steps=num_inference_steps,
        api_name="/infer"
    )

    # Prepare response
    response = {
        "filepath": result[0],
        "seed": result[1]
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
