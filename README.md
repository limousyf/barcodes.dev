# Barcode Generator Web Application

A Flask web application that generates barcodes from user input text and displays them as images. The application supports multiple barcode symbologies and image formats, designed to run on Google Cloud Compute Engine with SSL/HTTPS support.

## Features

- **Multiple Barcode Symbologies**: Support for 19 different barcode types including:
  - Code128 (Standard)
  - Code39
  - EAN (European Article Number)
  - EAN-13, EAN-8, EAN-14
  - UPC (Universal Product Code)
  - UPC-A
  - ISBN (Book) - ISBN-10, ISBN-13
  - ISSN (Serial Publication)
  - ITF (Interleaved 2 of 5)
  - GS1, GS1-128
  - Codabar
  - PZN (Pharmaceutical)
  - JAN (Japanese Article Number)
  - GTIN (Global Trade Item Number)

- **Multiple Image Formats**: Generate barcodes in:
  - PNG (Recommended - Best Quality)
  - JPEG (Smaller File Size)
  - WEBP (Modern Format)

- **Download Support**: Download generated barcodes in any supported format
- **Responsive Web Design**: Mobile-friendly interface
- **SSL/HTTPS Support**: Secure connections with Google-managed certificates
- **Docker Containerized**: Easy deployment and scaling

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

4. Access your application at `https://[EXTERNAL_IP]:8080` or via the configured domain

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
- python-barcode: Barcode generation library with support for multiple symbologies
- Pillow: Image processing and format conversion
- gunicorn: WSGI HTTP Server

## Supported Barcode Types

The application leverages the python-barcode library to support a wide range of barcode symbologies:

| Symbology | Use Case | Example Input |
|-----------|----------|---------------|
| Code128 | General purpose, alphanumeric | `ABC123` |
| Code39 | Industrial applications | `123ABC` |
| EAN-13 | Retail products (13 digits) | `1234567890123` |
| EAN-8 | Small retail products (8 digits) | `12345678` |
| UPC-A | North American retail | `012345678905` |
| ISBN-13 | Books (13 digits) | `9780123456789` |
| ISBN-10 | Books (10 digits) | `0123456789` |
| ISSN | Serial publications | `12345678` |
| ITF | Shipping containers | `1234567890` |
| GS1-128 | Supply chain | `(01)12345678901234` |

## Image Format Support

- **PNG**: Lossless compression, best for high-quality barcodes
- **JPEG**: Lossy compression, smaller file sizes
- **WEBP**: Modern format with excellent compression