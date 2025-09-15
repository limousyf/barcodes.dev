# Barcode Generator Web Application

A Flask web application that generates barcodes from user input text and displays them as images. The application is designed to run on Google Cloud Compute Engine.

## Features

- Generate Code128 barcodes from text input
- Display barcode images in the web interface
- Download generated barcodes as PNG files
- Responsive web design
- Docker containerized for easy deployment

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:8080`

## Google Cloud Deployment

### Prerequisites

1. Install Google Cloud SDK
2. Set up a Google Cloud project
3. Enable Container Registry API
4. Configure Docker to use gcloud as a credential helper:
```bash
gcloud auth configure-docker
```

### Deployment Steps

1. Update the `PROJECT_ID` in `deploy.sh` with your Google Cloud project ID

2. Run the deployment script:
```bash
./deploy.sh
```

3. Get the external IP of your instance:
```bash
gcloud compute instances describe barcode-generator --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

4. Access your application at `http://[EXTERNAL_IP]:8080`

## Alternative Deployment Methods

### Using App Engine

If you prefer App Engine over Compute Engine:

```bash
gcloud app deploy app.yaml
```

### Manual Compute Engine Setup

1. Create a Compute Engine instance
2. Install Docker on the instance
3. Clone this repository
4. Build and run the Docker container:
```bash
docker build -t barcode-generator .
docker run -p 8080:8080 barcode-generator
```

## Project Structure

```
barcodes.dev/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── app.yaml          # App Engine configuration
├── deploy.sh         # Deployment script
├── templates/
│   └── index.html    # Web interface template
└── static/           # Static files directory
```

## Dependencies

- Flask: Web framework
- python-barcode: Barcode generation library
- Pillow: Image processing
- gunicorn: WSGI HTTP Server