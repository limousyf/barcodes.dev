#!/bin/bash

# Deployment script for Google Cloud Compute Engine

# Set your project ID and instance details
PROJECT_ID="barcodesdev"
INSTANCE_NAME="barcode-generator"
ZONE="us-central1-a"
MACHINE_TYPE="e2-micro"

echo "Building and deploying Barcode Generator to Google Cloud Compute Engine..."

# Build Docker image
echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/barcode-generator .

# Push to Google Container Registry
echo "Pushing to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/barcode-generator

# Create or update the compute instance
echo "Creating/updating compute instance..."
gcloud compute instances create-with-container $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --container-image=gcr.io/$PROJECT_ID/barcode-generator \
    --container-restart-policy=always \
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
echo "Your application should be available at the external IP of the instance on port 8080"
echo "Get the external IP with: gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"