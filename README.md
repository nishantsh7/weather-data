# Historical Weather Data Service

This backend service provides an API to fetch historical weather data from the Open-Meteo API, store it in Google Cloud Storage (GCS), and retrieve the stored data. The service is built with Python (Flask) and designed to be deployed as a container on Google Cloud Run.

## Table of Contents

1. [Prerequisites](#1-prerequisites)  
2. [GCP Setup](#2-gcp-setup)  
3. [Local Development](#3-local-development)  
4. [Deployment to Google Cloud Run](#4-deployment-to-google-cloud-run)  
5. [API Endpoints](#5-api-endpoints)  
    - [POST /store-weather-data](#post-store-weather-data)  
    - [GET /list-weather-files](#get-list-weather-files)  
    - [GET /weather-file-contentltfile_namegt](#get-weather-file-contentltfile_namegt)

---

## 1. Prerequisites

- A Google Cloud Platform (GCP) project.
- `gcloud` CLI installed and authenticated.
- Docker installed on your local machine.

---

## 2. GCP Setup

### a. Enable APIs

Enable the necessary APIs for your project:

```bash
gcloud services enable run.googleapis.com
gcloud services enable storage-component.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### b. Create a GCS Bucket

Create a globally unique bucket to store the weather data JSON files:

```bash
export BUCKET_NAME="your-unique-bucket-name-here"
gsutil mb gs://$BUCKET_NAME
```

### c. Create a Service Account (Recommended)

Create a dedicated service account for the Cloud Run service to interact with GCS:

```bash
gcloud iam service-accounts create weather-service-sa \
    --display-name="Weather Service Account"
```

Grant the service account permissions to write to your GCS bucket:

```bash
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member="serviceAccount:weather-service-sa@$(gcloud config get-value project).iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

---

## 3. Local Development

Clone the repository or copy the files (`app.py`, `requirements.txt`, `Dockerfile`).

Authenticate for local testing (to allow `app.py` to access GCS):

```bash
gcloud auth application-default login
```

Set environment variables:

```bash
export GCS_BUCKET_NAME="your-unique-bucket-name-here"
```

Install dependencies and run locally:

```bash
pip install -r requirements.txt
flask run
```

The application will be running at `http://127.0.0.1:5000`.

---

## 4. Deployment to Google Cloud Run

Set environment variables for deployment:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export BUCKET_NAME="your-unique-bucket-name-here"
export SERVICE_NAME="weather-api-service"
export REGION="us-central1"  # or your preferred region
```

Build the Docker image using Cloud Build and store it in Artifact Registry:

```bash
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/weather-repo/${SERVICE_NAME}
```

Deploy to Cloud Run:

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/weather-repo/${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --service-account "weather-service-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars "GCS_BUCKET_NAME=${BUCKET_NAME}"
```

> `--allow-unauthenticated` makes the service publicly accessible. Remove this flag if you want to manage access with IAM.

After deployment, `gcloud` will provide you with the Service URL.

---

## 5. API Endpoints

> Replace `SERVICE_URL` with the URL provided after Cloud Run deployment.

---

### POST `/store-weather-data`

Fetches and stores weather data.

**Request:**

```bash
curl -X POST ${SERVICE_URL}/store-weather-data \
-H "Content-Type: application/json" \
-d '{
  "latitude": 35.6895,
  "longitude": 139.6917,
  "start_date": "2023-01-01",
  "end_date": "2023-01-07"
}'
```

**Success Response (201):**

```json
{
  "message": "Weather data stored successfully",
  "file_name": "weather_35.6895_139.6917_2023-01-01_2023-01-07_20231027103000.json"
}
```

---

### GET `/list-weather-files`

Lists all stored files in the GCS bucket.

**Request:**

```bash
curl ${SERVICE_URL}/list-weather-files
```

**Success Response (200):**

```json
[
  "weather_35.6895_139.6917_2023-01-01_2023-01-07_20231027103000.json",
  "weather_40.7128_-74.0060_2022-12-20_2022-12-25_20231027103510.json"
]
```

---

### GET `/weather-file-content/<file_name>`

Retrieves the content of a specific file.

**Request:**

> URL-encode the filename if necessary, but it should be safe with this naming convention.

```bash
curl ${SERVICE_URL}/weather-file-content/weather_35.6895_139.6917_2023-01-01_2023-01-07_20231027103000.json
```

**Success Response (200):**

```json
{
  "latitude": 35.7,
  "longitude": 139.7,
  "generationtime_ms": 0.58,
  "utc_offset_seconds": 32400,
  "timezone": "Asia/Tokyo",
  "timezone_abbreviation": "JST",
  "elevation": 40.0,
  "daily_units": {
    "time": "iso8601",
    "temperature_2m_max": "°C",
    ...
  },
  "daily": {
    "time": [
      "2023-01-01",
      "2023-01-02",
      ...
    ],
    "temperature_2m_max": [
      11.2,
      12.5,
      ...
    ],
    ...
  }
}
```
