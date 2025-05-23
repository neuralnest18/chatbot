import os
from flask import Flask, render_template, request, jsonify
import aiml
import time

app = Flask(__name__)

# Initialize AIML kernel and load AIML files
aiml_directory = os.path.join(os.path.dirname(__file__), 'aimlfile')
kernel = aiml.Kernel()

# Function to load AIML files and handle errors
def load_aiml_files(aiml_directory):
    for filename in os.listdir(aiml_directory):
        try:
            full_path = os.path.join(aiml_directory, filename)
            print(f"Loading {full_path}...")
            start_time = time.perf_counter()
            kernel.learn(full_path)
            end_time = time.perf_counter()
            print(f"Loaded {filename} successfully in {(end_time - start_time):.2f} seconds.")
        except Exception as e:
            print(f"Failed to load {filename}: {e}")

load_aiml_files(aiml_directory)

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get')
def get_bot_response():
    user_text = request.args.get('msg')
    bot_response = kernel.respond(user_text)
    return jsonify({'response': bot_response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
