# Google Cloud Project Setup Guide

## Prerequisites

1. **Google Account**: You need a Google account to access Google Cloud Platform
2. **Billing Account**: Google Cloud requires a billing account (free tier available)

## Option 1: Manual Setup via Web Console

### Step 1: Access Google Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account

### Step 2: Create a New Project
1. Click the project dropdown at the top of the page
2. Click "New Project"
3. Enter project details:
   - **Project name**: `barcode-generator` (or your preferred name)
   - **Project ID**: Will be auto-generated (note this down - you'll need it)
   - **Organization**: Select if applicable
4. Click "Create"

### Step 3: Enable Required APIs
1. Go to "APIs & Services" > "Library"
2. Enable these APIs:
   - **Compute Engine API**
   - **Container Registry API**
   - **Cloud Build API**

### Step 4: Set up Billing
1. Go to "Billing" in the left menu
2. Link a billing account or create a new one
3. Google offers $300 free credit for new accounts

## Option 2: Automated Setup via CLI

### Step 1: Install Google Cloud SDK
```bash
# macOS (using Homebrew)
brew install --cask google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

### Step 2: Run the Setup Script
Use the provided `setup-gcp-project.sh` script (see below)

## Getting Your Project ID

After creating the project, you'll need the Project ID for deployment:

1. **From Console**: Visible in the project dropdown
2. **From CLI**: Run `gcloud projects list`
3. **From Script**: The setup script will display it

## Next Steps

1. Update `deploy.sh` with your project ID
2. Run `./setup-gcp-project.sh` to configure your project
3. Deploy your application with `./deploy.sh`