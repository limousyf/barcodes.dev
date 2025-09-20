#!/bin/bash

# Deployment script for Google Cloud Compute Engine

# Set your project ID and instance details
PROJECT_ID="barcodesdev"
INSTANCE_NAME="barcode-generator"
ZONE="us-central1-a"
MACHINE_TYPE="e2-micro"

# Database configuration
DB_HOST="34.69.80.105"
DB_NAME="barcode_db"
DB_USER="barcode_user"
DB_PASS="barcode_pass"
DATABASE_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:5432/$DB_NAME"

echo "Building and deploying Barcode Generator to Google Cloud Compute Engine..."

# Build Docker image for AMD64 architecture (production compatibility)
echo "Building Docker image for AMD64..."
docker buildx build --platform linux/amd64 --no-cache -t gcr.io/$PROJECT_ID/barcode-generator . --push

# Image is already pushed by buildx, skip separate push step
echo "Docker image built and pushed successfully"

# Check if instance exists and delete it to ensure clean deployment
echo "Checking for existing instance..."
if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
    echo "Deleting existing instance..."
    gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --quiet
fi

# Create the compute instance with PostgreSQL environment variable
echo "Creating compute instance with PostgreSQL configuration..."
gcloud compute instances create-with-container $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --container-image=gcr.io/$PROJECT_ID/barcode-generator \
    --container-restart-policy=always \
    --container-env=DATABASE_URL="$DATABASE_URL" \
    --tags=http-server,https-server \
    --project=$PROJECT_ID

# Create firewall rule for HTTP traffic (if not exists)
echo "Setting up firewall rules..."
gcloud compute firewall-rules create allow-http-8080 \
    --allow tcp:8080 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --project=$PROJECT_ID \
    --quiet || echo "Firewall rule already exists"

echo "Deployment complete!"
echo ""
echo "📊 Deployment Summary:"
echo "====================="
echo "Project ID: $PROJECT_ID"
echo "Instance Name: $INSTANCE_NAME"
echo "Zone: $ZONE"
echo "Database: PostgreSQL (Cloud SQL)"
echo ""

# Get and display the external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)' --project=$PROJECT_ID)
echo "🌐 Access Information:"
echo "====================="
echo "External IP: $EXTERNAL_IP"
echo "Web Interface: http://$EXTERNAL_IP:8080"
echo "Barcode API: POST http://$EXTERNAL_IP:8080/api/barcode"
echo "QR Code API: POST http://$EXTERNAL_IP:8080/api/qrcode"
echo ""
echo "💡 Next Steps:"
echo "- Update your DNS A record for barcodes.dev to point to: $EXTERNAL_IP"
echo "- Wait 2-3 minutes for the container to fully start"
echo "- Test the APIs using the endpoints above"