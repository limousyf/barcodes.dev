#!/bin/bash

# Google Cloud Project Setup Script for Barcode Generator

set -e

echo "🚀 Google Cloud Project Setup for Barcode Generator"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Login to Google Cloud (if not already logged in)
echo "🔐 Checking Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "Please log in to Google Cloud:"
    gcloud auth login
else
    echo "✅ Already authenticated"
fi

# Prompt for project details
echo ""
echo "📝 Project Configuration"
echo "----------------------"

read -p "Enter project name (e.g., 'Barcode Generator'): " PROJECT_NAME
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="Barcode Generator"
fi

read -p "Enter project ID (must be globally unique, e.g., 'barcode-gen-$(date +%s)'): " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID="barcode-gen-$(date +%s)"
fi

echo "Using Project Name: $PROJECT_NAME"
echo "Using Project ID: $PROJECT_ID"

# Create the project
echo ""
echo "🏗️  Creating Google Cloud Project..."
if gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"; then
    echo "✅ Project created successfully!"
else
    echo "❌ Failed to create project. The project ID might already exist."
    echo "Try with a different project ID."
    exit 1
fi

# Set the project as default
echo "🔧 Setting project as default..."
gcloud config set project "$PROJECT_ID"

# Check if billing account exists
echo ""
echo "💳 Checking billing account..."
BILLING_ACCOUNTS=$(gcloud billing accounts list --format="value(name)" --filter="open:true")

if [ -z "$BILLING_ACCOUNTS" ]; then
    echo "⚠️  No billing account found."
    echo "Please set up billing at: https://console.cloud.google.com/billing"
    echo "You can continue with the free tier, but some services may be limited."
    read -p "Press Enter to continue or Ctrl+C to exit..."
else
    BILLING_ACCOUNT=$(echo "$BILLING_ACCOUNTS" | head -n1)
    echo "💳 Linking billing account: $BILLING_ACCOUNT"
    gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
    echo "✅ Billing account linked!"
fi

# Enable required APIs
echo ""
echo "🔌 Enabling required APIs..."
APIS=(
    "compute.googleapis.com"
    "containerregistry.googleapis.com"
    "cloudbuild.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo "Enabling $api..."
    gcloud services enable "$api"
done
echo "✅ All APIs enabled!"

# Set up default compute region/zone
echo ""
echo "🌍 Setting up default compute region/zone..."
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
echo "✅ Default region set to us-central1, zone us-central1-a"

# Configure Docker for Container Registry
echo ""
echo "🐳 Configuring Docker for Container Registry..."
gcloud auth configure-docker --quiet
echo "✅ Docker configured for gcr.io"

# Update deploy.sh with the project ID
echo ""
echo "📝 Updating deployment script with project ID..."
if [ -f "deploy.sh" ]; then
    sed -i.bak "s/PROJECT_ID=\"your-project-id\"/PROJECT_ID=\"$PROJECT_ID\"/" deploy.sh
    echo "✅ Updated deploy.sh with your project ID"
else
    echo "⚠️  deploy.sh not found in current directory"
fi

# Summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo "Project Name: $PROJECT_NAME"
echo "Project ID: $PROJECT_ID"
echo "Region: us-central1"
echo "Zone: us-central1-a"
echo ""
echo "🚀 Next Steps:"
echo "1. Your deploy.sh has been updated with the project ID"
echo "2. Run './deploy.sh' to deploy your barcode generator"
echo "3. Visit the Google Cloud Console: https://console.cloud.google.com/compute/instances?project=$PROJECT_ID"
echo ""
echo "💡 Useful Commands:"
echo "gcloud projects list                    # List all projects"
echo "gcloud compute instances list          # List compute instances"
echo "gcloud config list                     # Show current configuration"