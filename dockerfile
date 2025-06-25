# --- Base Image ---
# Use an official Python runtime as a parent image
FROM python:3.9-slim

# --- Environment Variables ---
# Set the working directory in the container
WORKDIR /app

# Set environment variables for the Flask application
# The PORT variable is used by Cloud Run to route traffic to the container.
ENV PORT 8080
# You MUST set this environment variable during deployment on Cloud Run
# to the name of your GCS bucket.
ENV GCS_BUCKET_NAME inrisk_weather_data

# --- System Dependencies ---
# Install any needed system packages
# (Not needed for this specific application, but good practice to have the layer)
# RUN apt-get update && apt-get install -y ...

# --- Application Dependencies ---
# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- Application Code ---
# Copy the rest of the application code into the container
COPY . .

# --- Expose Port and Run Application ---
# Expose the port the app runs on
EXPOSE 8080

# Use gunicorn for a production-ready web server.
# It will listen on the port specified by the PORT environment variable.
# The command specifies 4 worker processes and binds to all available
# network interfaces on the port defined by $PORT.
CMD exec gunicorn --workers 4 --bind 0.0.0.0:$PORT app:app
