#!/bin/bash
# Environment Variables Update Template
# This script helps you update your .env file with new credentials
# Run: bash update_env_template.sh

echo "=========================================="
echo "Credential Update Helper"
echo "=========================================="
echo ""
echo "This script will help you update your .env file"
echo "Make sure you have your new credentials ready!"
echo ""
read -p "Press Enter to continue..."

# Check if .env exists
if [ ! -f "server/.env" ]; then
    echo "Creating server/.env file..."
    touch server/.env
fi

echo ""
echo "=========================================="
echo "1. Spotify API Keys"
echo "=========================================="
read -p "Enter new SPOTIPY_CLIENT_ID: " spotify_id
read -p "Enter new SPOTIPY_CLIENT_SECRET: " spotify_secret

echo ""
echo "=========================================="
echo "2. Gmail Credentials"
echo "=========================================="
read -p "Enter EMAIL_HOST_USER (default: hemonterroddur@gmail.com): " email_user
email_user=${email_user:-hemonterroddur@gmail.com}
read -p "Enter EMAIL_HOST_PASSWORD (App Password recommended): " email_pass

echo ""
echo "=========================================="
echo "3. Google API Key (Gemini)"
echo "=========================================="
read -p "Enter new GOOGLE_API_KEY: " google_key

echo ""
echo "=========================================="
echo "4. Database Credentials"
echo "=========================================="
read -p "Enter DB_NAME (default: soundly_prod): " db_name
db_name=${db_name:-soundly_prod}
read -p "Enter DB_USER (default: soundly_user): " db_user
db_user=${db_user:-soundly_user}
read -p "Enter DB_PASSWORD: " db_pass
read -p "Enter DB_HOST (default: db): " db_host
db_host=${db_host:-db}
read -p "Enter DB_PORT (default: 5432): " db_port
db_port=${db_port:-5432}

echo ""
echo "=========================================="
echo "5. Django Secret Key"
echo "=========================================="
read -p "Enter SECRET_KEY (or press Enter to generate): " secret_key
if [ -z "$secret_key" ]; then
    secret_key=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    echo "Generated SECRET_KEY: $secret_key"
fi

echo ""
echo "=========================================="
echo "Updating .env file..."
echo "=========================================="

# Backup existing .env
if [ -f "server/.env" ]; then
    cp server/.env server/.env.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backed up existing .env file"
fi

# Write to .env file
cat > server/.env << EOF
# Django Settings
SECRET_KEY=$secret_key
DEBUG=False
ALLOWED_HOSTS=api.soundlybeats.com
CSRF_TRUSTED_ORIGINS=https://api.soundlybeats.com,https://soundly-beats.vercel.app

# Database
DB_NAME=$db_name
DB_USER=$db_user
DB_PASSWORD=$db_pass
DB_HOST=$db_host
DB_PORT=$db_port

# Spotify API
SPOTIPY_CLIENT_ID=$spotify_id
SPOTIPY_CLIENT_SECRET=$spotify_secret

# Email (Gmail)
DEFAULT_FROM_EMAIL=$email_user
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=$email_user
EMAIL_HOST_PASSWORD=$email_pass

# Google AI (Gemini)
GOOGLE_API_KEY=$google_key

# Firebase (keeping old credentials as requested)
# FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# JWT Settings
JWT_AUTH_SECURE=True
JWT_AUTH_HTTPONLY=True
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60

# CORS
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://www.soundlybeats.com,https://soundly-beats.vercel.app

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
EOF

echo ""
echo "✅ .env file updated successfully!"
echo ""
echo "Next steps:"
echo "1. Review server/.env to ensure all values are correct"
echo "2. Test your application with the new credentials"
echo "3. Update production environment variables on your deployment platform"
echo ""
echo "⚠️  Remember: Never commit .env files to git!"
