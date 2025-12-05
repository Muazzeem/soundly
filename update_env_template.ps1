# PowerShell script to update .env file with new credentials
# Run: .\update_env_template.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Credential Update Helper" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will help you update your .env file" -ForegroundColor Yellow
Write-Host "Make sure you have your new credentials ready!" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to continue"

# Check if .env exists
$envPath = "server\.env"
if (-not (Test-Path $envPath)) {
    Write-Host "Creating server\.env file..." -ForegroundColor Green
    New-Item -Path $envPath -ItemType File -Force | Out-Null
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "1. Spotify API Keys" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$spotifyId = Read-Host "Enter new SPOTIPY_CLIENT_ID"
$spotifySecret = Read-Host "Enter new SPOTIPY_CLIENT_SECRET"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "2. Gmail Credentials" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$emailUser = Read-Host "Enter EMAIL_HOST_USER (default: hemonterroddur@gmail.com)"
if ([string]::IsNullOrWhiteSpace($emailUser)) {
    $emailUser = "hemonterroddur@gmail.com"
}
$emailPass = Read-Host "Enter EMAIL_HOST_PASSWORD (App Password recommended)" -AsSecureString
$emailPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($emailPass)
)

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "3. Google API Key (Gemini)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$googleKey = Read-Host "Enter new GOOGLE_API_KEY"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "4. Database Credentials" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$dbName = Read-Host "Enter DB_NAME (default: soundly_prod)"
if ([string]::IsNullOrWhiteSpace($dbName)) {
    $dbName = "soundly_prod"
}
$dbUser = Read-Host "Enter DB_USER (default: soundly_user)"
if ([string]::IsNullOrWhiteSpace($dbUser)) {
    $dbUser = "soundly_user"
}
$dbPass = Read-Host "Enter DB_PASSWORD" -AsSecureString
$dbPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPass)
)
$dbHost = Read-Host "Enter DB_HOST (default: db)"
if ([string]::IsNullOrWhiteSpace($dbHost)) {
    $dbHost = "db"
}
$dbPort = Read-Host "Enter DB_PORT (default: 5432)"
if ([string]::IsNullOrWhiteSpace($dbPort)) {
    $dbPort = "5432"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "5. Django Secret Key" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
$secretKey = Read-Host "Enter SECRET_KEY (or press Enter to generate)"
if ([string]::IsNullOrWhiteSpace($secretKey)) {
    # Generate Django secret key
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)"
    $secretKey = ""
    for ($i = 0; $i -lt 50; $i++) {
        $secretKey += $chars[(Get-Random -Maximum $chars.Length)]
    }
    Write-Host "Generated SECRET_KEY: $secretKey" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Updating .env file..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Backup existing .env
if (Test-Path $envPath) {
    $backupPath = "server\.env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $envPath $backupPath
    Write-Host "Backed up existing .env file to $backupPath" -ForegroundColor Green
}

# Write to .env file
$envContent = @"
# Django Settings
SECRET_KEY=$secretKey
DEBUG=False
ALLOWED_HOSTS=api.soundlybeats.com
CSRF_TRUSTED_ORIGINS=https://api.soundlybeats.com,https://soundly-beats.vercel.app

# Database
DB_NAME=$dbName
DB_USER=$dbUser
DB_PASSWORD=$dbPassPlain
DB_HOST=$dbHost
DB_PORT=$dbPort

# Spotify API
SPOTIPY_CLIENT_ID=$spotifyId
SPOTIPY_CLIENT_SECRET=$spotifySecret

# Email (Gmail)
DEFAULT_FROM_EMAIL=$emailUser
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=$emailUser
EMAIL_HOST_PASSWORD=$emailPassPlain

# Google AI (Gemini)
GOOGLE_API_KEY=$googleKey

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
"@

Set-Content -Path $envPath -Value $envContent

Write-Host ""
Write-Host "✅ .env file updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Review server\.env to ensure all values are correct"
Write-Host "2. Test your application with the new credentials"
Write-Host "3. Update production environment variables on your deployment platform"
Write-Host ""
Write-Host "⚠️  Remember: Never commit .env files to git!" -ForegroundColor Red
