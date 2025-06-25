import os
import json
import requests
from flask import Flask, request, jsonify
from google.cloud import storage
from datetime import datetime

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'your-gcs-bucket-name')

# --- Google Cloud Storage Client ---
try:
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
except Exception as e:
    print(f"Error initializing GCS client: {e}")
    storage_client = None
    bucket = None

# --- Open-Meteo API Configuration ---
OPEN_METEO_API_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_WEATHER_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "apparent_temperature_mean"
]

# --- Helper Functions ---
def validate_date(date_string):
    """Validates that a string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# --- API Endpoints ---

@app.route('/store-weather-data', methods=['POST'])
def store_weather_data():
    if not storage_client or not bucket:
        return jsonify({"error": "Google Cloud Storage is not configured properly."}), 500

    # 1. Get and validate request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    lat = data.get('latitude')
    lon = data.get('longitude')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not all([lat, lon, start_date, end_date]):
        return jsonify({"error": "Missing required fields: latitude, longitude, start_date, end_date"}), 400

    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return jsonify({"error": "Latitude and longitude must be numbers"}), 400

    if not (validate_date(start_date) and validate_date(end_date)):
        return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400

    # 2. Fetch data from Open-Meteo API
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(DAILY_WEATHER_VARS),
            "timezone": "auto"
        }
        response = requests.get(OPEN_METEO_API_URL, params=params)
        response.raise_for_status()  
        weather_data = response.json()

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch data from Open-Meteo: {e}"}), 502 # Bad Gateway

    # 3. Store data in Google Cloud Storage
    try:
        
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_name = f"weather_{lat}_{lon}_{start_date}_{end_date}_{timestamp}.json"

        
        blob = bucket.blob(file_name)

        
        blob.upload_from_string(
            json.dumps(weather_data, indent=2),
            content_type='application/json'
        )
    except Exception as e:
        
        print(f"Error uploading to GCS: {e}")
        return jsonify({"error": "Failed to store data in Google Cloud Storage"}), 500

    # 4. Return success response
    return jsonify({
        "message": "Weather data stored successfully",
        "file_name": file_name
    }), 201

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Welcome to the Historical Weather Data API 🌤️",
        "endpoints": {
            "POST /store-weather-data": "Fetch and store weather data in GCS",
            "GET /list-weather-files": "List stored weather data files",
            "GET /weather-file-content/file_name": "Retrieve content of a specific file"
        }
    }), 200

@app.route('/list-weather-files', methods=['GET'])
def list_weather_files():
    """Lists all weather data files stored in the GCS bucket."""
    if not storage_client or not bucket:
        return jsonify({"error": "Google Cloud Storage is not configured properly."}), 500

    try:
        blobs = storage_client.list_blobs(GCS_BUCKET_NAME)
        file_names = [blob.name for blob in blobs]
        return jsonify(file_names), 200
    except Exception as e:
        print(f"Error listing files from GCS: {e}")
        return jsonify({"error": "Failed to list files from Google Cloud Storage"}), 500

@app.route('/weather-file-content/<string:file_name>', methods=['GET'])
def get_weather_file_content(file_name):
    """Fetches and returns the content of a specific JSON file from GCS."""
    if not storage_client or not bucket:
        return jsonify({"error": "Google Cloud Storage is not configured properly."}), 500

    try:
        blob = bucket.blob(file_name)

        if not blob.exists():
            return jsonify({"error": "File not found"}), 404

        
        file_contents = blob.download_as_string()
        return jsonify(json.loads(file_contents)), 200

    except Exception as e:
        print(f"Error retrieving file from GCS: {e}")
        return jsonify({"error": "Failed to retrieve file content from Google Cloud Storage"}), 500


if __name__ == '__main__':
    # This is used for local development.
    # When deployed to Cloud Run, a production WSGI server like Gunicorn will be used.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
