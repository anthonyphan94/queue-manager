#!/bin/bash
# ============================================
# GCP Cloud Run Setup Script
# ============================================
# Run this ONCE to set up all GCP resources
# Prerequisites: gcloud CLI installed & authenticated
# ============================================

set -e  # Exit on error

# ============================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================
export PROJECT_ID="mbl-queue-manager"        # Your GCP project ID
export REGION="us-central1"                     # Preferred region
export GITHUB_REPO="anthonyphan94/queue-manager" # Your GitHub repo (owner/repo)

# Derived values (no need to change)
export SERVICE_NAME="salon-turn-manager"
export REPOSITORY_NAME="salon-manager"
export BUCKET_NAME="${PROJECT_ID}-salon-data"
export SERVICE_ACCOUNT="github-deploy"
export WORKLOAD_IDENTITY_POOL="github-pool"
export WORKLOAD_IDENTITY_PROVIDER="github-provider"

echo "============================================"
echo "GCP Cloud Run Setup for Salon Turn Manager"
echo "============================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "GitHub Repo: $GITHUB_REPO"
echo "============================================"

# ============================================
# 1. Enable Required APIs
# ============================================
echo ""
echo "📦 Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    iam.googleapis.com \
    iamcredentials.googleapis.com \
    storage.googleapis.com \
    --project=$PROJECT_ID

# ============================================
# 2. Create Artifact Registry Repository
# ============================================
echo ""
echo "🐳 Creating Artifact Registry repository..."
gcloud artifacts repositories create $REPOSITORY_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Salon Turn Manager Docker images" \
    --project=$PROJECT_ID \
    2>/dev/null || echo "Repository already exists"

# ============================================
# 3. Create Cloud Storage Bucket for SQLite
# ============================================
echo ""
echo "🗄️ Creating Cloud Storage bucket for data persistence..."
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --uniform-bucket-level-access \
    --project=$PROJECT_ID \
    2>/dev/null || echo "Bucket already exists"

# ============================================
# 4. Create Service Account for GitHub Actions
# ============================================
echo ""
echo "👤 Creating service account for GitHub Actions..."
gcloud iam service-accounts create $SERVICE_ACCOUNT \
    --display-name="GitHub Actions Deploy" \
    --description="Service account for GitHub Actions CI/CD" \
    --project=$PROJECT_ID \
    2>/dev/null || echo "Service account already exists"

SA_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary permissions
echo "🔐 Granting permissions to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.admin" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/artifactregistry.writer" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.admin" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/iam.serviceAccountUser" \
    --quiet

# ============================================
# 5. Set up Workload Identity Federation
# ============================================
echo ""
echo "🔗 Setting up Workload Identity Federation..."

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Create Workload Identity Pool
gcloud iam workload-identity-pools create $WORKLOAD_IDENTITY_POOL \
    --location="global" \
    --display-name="GitHub Actions Pool" \
    --description="Pool for GitHub Actions authentication" \
    --project=$PROJECT_ID \
    2>/dev/null || echo "Pool already exists"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc $WORKLOAD_IDENTITY_PROVIDER \
    --location="global" \
    --workload-identity-pool=$WORKLOAD_IDENTITY_POOL \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --project=$PROJECT_ID \
    2>/dev/null || echo "Provider already exists"

# Allow GitHub repo to impersonate service account
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WORKLOAD_IDENTITY_POOL/attribute.repository/$GITHUB_REPO" \
    --project=$PROJECT_ID \
    --quiet

# ============================================
# 6. Output Configuration for GitHub
# ============================================
echo ""
echo "============================================"
echo "✅ GCP SETUP COMPLETE!"
echo "============================================"
echo ""
echo "📋 Add these to your GitHub workflow (.github/workflows/deploy.yml):"
echo ""
echo "  GCP_PROJECT_ID: '$PROJECT_ID'"
echo "  GCP_PROJECT_NUMBER: '$PROJECT_NUMBER'"
echo "  GCP_REGION: '$REGION'"
echo ""
echo "📋 Workload Identity Provider:"
echo "  projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WORKLOAD_IDENTITY_POOL/providers/$WORKLOAD_IDENTITY_PROVIDER"
echo ""
echo "📋 Service Account:"
echo "  $SA_EMAIL"
echo ""
echo "============================================"
echo "🚀 Next Steps:"
echo "1. Update .github/workflows/deploy.yml with the values above"
echo "2. Commit and push to the 'main' branch"
echo "3. Watch GitHub Actions deploy your app!"
echo "============================================"
