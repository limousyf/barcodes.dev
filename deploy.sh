#!/bin/bash

# Deployment script for Google Cloud Compute Engine

# Set your project ID and instance details
PROJECT_ID="barcodesdev"
INSTANCE_NAME="barcode-generator"
ZONE="us-central1-a"
MACHINE_TYPE="e2-micro"

# Database configuration
DB_HOST="34.69.80.105"
DB_NAME="barcode_records"
DB_USER="barcode_user"
DB_PASS="barcode_pass"
DATABASE_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:5432/$DB_NAME"

# Static IP configuration
STATIC_IP_NAME="barcode-static-ip"
STATIC_IP_ADDRESS="34.61.233.111"

# Load balancer configuration  
LOAD_BALANCER_IP="34.49.2.152"

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

# Create the compute instance with PostgreSQL environment variable and static IP
echo "Creating compute instance with PostgreSQL configuration and static IP..."
gcloud compute instances create-with-container $INSTANCE_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --container-image=gcr.io/$PROJECT_ID/barcode-generator \
    --container-restart-policy=always \
    --container-env=DATABASE_URL="$DATABASE_URL" \
    --address=$STATIC_IP_ADDRESS \
    --tags=http-server,https-server \
    --project=$PROJECT_ID

# Create firewall rules for HTTP traffic (if not exists)
echo "Setting up firewall rules..."
gcloud compute firewall-rules create allow-http-8080 \
    --allow tcp:8080 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --project=$PROJECT_ID \
    --quiet || echo "Firewall rule for port 8080 already exists"

gcloud compute firewall-rules create allow-http-80 \
    --allow tcp:80 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server \
    --project=$PROJECT_ID \
    --quiet || echo "Firewall rule for port 80 already exists"

# Add instance to load balancer instance group
echo "Adding instance to load balancer..."
gcloud compute instance-groups unmanaged add-instances barcode-instance-group \
    --instances=$INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --quiet || echo "Instance already in load balancer group"

echo "Deployment complete!"
echo ""
echo "📊 Deployment Summary:"
echo "====================="
echo "Project ID: $PROJECT_ID"
echo "Instance Name: $INSTANCE_NAME"
echo "Zone: $ZONE"
echo "Database: PostgreSQL (Cloud SQL)"
echo ""

# Display access information
echo "🌐 Access Information:"
echo "====================="
echo "Instance IP: $STATIC_IP_ADDRESS (port 8080 only)"
echo "Load Balancer IP: $LOAD_BALANCER_IP (port 80 & 8080)"
echo ""
echo "Web Interface (port 80): http://$LOAD_BALANCER_IP"
echo "Web Interface (port 8080): http://$LOAD_BALANCER_IP:8080"
echo "Barcode API: POST http://$LOAD_BALANCER_IP/api/barcode"
echo "QR Code API: POST http://$LOAD_BALANCER_IP/api/qrcode"
echo ""
echo "💡 Next Steps:"
echo "- Update your DNS A record for barcodes.dev to point to: $LOAD_BALANCER_IP"
echo "- This enables access via http://barcodes.dev (port 80)"
echo "- Wait 2-3 minutes for the container to fully start"
echo "- Test the APIs using the endpoints above"