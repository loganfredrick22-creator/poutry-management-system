# FarmLink XAMPP Automated Setup Script
# This script automates the complete XAMPP deployment process

param(
    [string]$MySQLHost = "localhost",
    [string]$MySQLPort = "3306", 
    [string]$MySQLUser = "root",
    [string]$MySQLPassword = "",
    [string]$DatabaseName = "farmlink",
    [string]$AppPort = "5000",
    [switch]$MigrateData = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== FarmLink XAMPP Setup Script ===" -ForegroundColor Green
Write-Host "This script will set up FarmLink with MySQL on XAMPP" -ForegroundColor Cyan
Write-Host ""

# Function to check if XAMPP is installed
function Test-XAMPP {
    $xamppPaths = @(
        "C:\xampp",
        "C:\xampp7", 
        "C:\xampp8",
        "D:\xampp",
        "${env:ProgramFiles}\xampp",
        "${env:ProgramFiles(x86)}\xampp"
    )
    
    foreach ($path in $xamppPaths) {
        if (Test-Path "$path\mysql\bin\mysql.exe") {
            return $path
        }
    }
    return $null
}

# Function to check if MySQL is running
function Test-MySQLRunning {
    try {
        $result = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
        return $result -ne $null
    }
    catch {
        return $false
    }
}

# Function to create .env file
function New-EnvFile {
    $envContent = @"
# FarmLink Configuration for XAMPP
FARMLINK_DB_TYPE=mysql
FARMLINK_MYSQL_HOST=$MySQLHost
FARMLINK_MYSQL_PORT=$MySQLPort
FARMLINK_MYSQL_USER=$MySQLUser
FARMLINK_MYSQL_PASSWORD=$MySQLPassword
FARMLINK_MYSQL_DATABASE=$DatabaseName

# Access Control - Enable editing for all users when hosted
FARMLINK_EDIT_MODE=all_users
FARMLINK_ENABLE_EDITING_FOR_ALL=true

# Security - Change this in production!
FARMLINK_SECRET_KEY=farmlink-secret-key-$(Get-Random -Minimum 1000 -Maximum 9999)
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Created .env file" -ForegroundColor Green
}

# Function to setup MySQL database
function Setup-MySQLDatabase {
    param($xamppPath)
    
    Write-Host "Setting up MySQL database..." -ForegroundColor Yellow
    
    $mysqlExe = "$xamppPath\mysql\bin\mysql.exe"
    $sqlFile = "database\setup_mysql.sql"
    
    if (-not (Test-Path $sqlFile)) {
        Write-Host "❌ SQL setup file not found: $sqlFile" -ForegroundColor Red
        return $false
    }
    
    try {
        # Create database and tables
        $mysqlCmd = "`"$mysqlExe`" --host=$MySQLHost --port=$MySQLPort --user=$MySQLUser"
        if ($MySQLPassword) {
            $mysqlCmd += " --password=$MySQLPassword"
        }
        
        Write-Host "Executing MySQL setup script..." -ForegroundColor Cyan
        $result = & cmd /c "$mysqlCmd < `"$sqlFile`"" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ MySQL database setup completed" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ MySQL setup failed:" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Error setting up MySQL database: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to setup Python environment
function Setup-PythonEnvironment {
    Write-Host "Setting up Python environment..." -ForegroundColor Yellow
    
    try {
        # Check if Python is available
        $pythonVersion = python --version 2>&1
        Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan
        
        # Create virtual environment if it doesn't exist
        if (-not (Test-Path ".venv")) {
            Write-Host "Creating virtual environment..." -ForegroundColor Cyan
            python -m venv .venv
        }
        
        # Activate virtual environment
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        & ".venv\Scripts\Activate.ps1"
        
        # Upgrade pip
        Write-Host "Upgrading pip..." -ForegroundColor Cyan
        python -m pip install --upgrade pip
        
        # Install requirements
        Write-Host "Installing requirements..." -ForegroundColor Cyan
        pip install -r requirements.txt
        
        Write-Host "✅ Python environment setup completed" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Error setting up Python environment: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to migrate data from SQLite
function Migrate-SQLiteData {
    Write-Host "Migrating SQLite data to MySQL..." -ForegroundColor Yellow
    
    if (-not (Test-Path "farmlink.db")) {
        Write-Host "⚠️  No SQLite database found. Skipping migration." -ForegroundColor Yellow
        return $true
    }
    
    try {
        # Set environment variables for migration
        $env:FARMLINK_DB_TYPE = "mysql"
        $env:FARMLINK_MYSQL_HOST = $MySQLHost
        $env:FARMLINK_MYSQL_PORT = $MySQLPort
        $env:FARMLINK_MYSQL_USER = $MySQLUser
        $env:FARMLINK_MYSQL_PASSWORD = $MySQLPassword
        $env:FARMLINK_MYSQL_DATABASE = $DatabaseName
        
        # Run migration script
        python database\migrate_sqlite_to_mysql.py
        
        Write-Host "✅ Data migration completed" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Error migrating data: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to start the application
function Start-Application {
    Write-Host "Starting FarmLink application..." -ForegroundColor Yellow
    
    try {
        # Set environment variables
        $env:FARMLINK_DB_TYPE = "mysql"
        $env:FARMLINK_MYSQL_HOST = $MySQLHost
        $env:FARMLINK_MYSQL_PORT = $MySQLPort
        $env:FARMLINK_MYSQL_USER = $MySQLUser
        $env:FARMLINK_MYSQL_PASSWORD = $MySQLPassword
        $env:FARMLINK_MYSQL_DATABASE = $DatabaseName
        $env:FARMLINK_EDIT_MODE = "all_users"
        $env:FARMLINK_ENABLE_EDITING_FOR_ALL = "true"
        
        Write-Host "Application will be available at: http://127.0.0.1:$AppPort/login" -ForegroundColor Green
        Write-Host "Default login: admin / admin123" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Press Ctrl+C to stop the application" -ForegroundColor Yellow
        Write-Host ""
        
        # Start the application
        python app.py
    }
    catch {
        Write-Host "❌ Error starting application: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main execution
try {
    Write-Host "Checking prerequisites..." -ForegroundColor Cyan
    
    # Check XAMPP installation
    $xamppPath = Test-XAMPP
    if (-not $xamppPath) {
        Write-Host "❌ XAMPP not found. Please install XAMPP first." -ForegroundColor Red
        Write-Host "Download from: https://www.apachefriends.org/" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "✅ XAMPP found at: $xamppPath" -ForegroundColor Green
    
    # Check if MySQL is running
    if (-not (Test-MySQLRunning)) {
        Write-Host "❌ MySQL is not running. Please start MySQL from XAMPP Control Panel." -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ MySQL is running" -ForegroundColor Green
    
    # Create .env file
    New-EnvFile
    
    # Setup MySQL database
    if (-not (Setup-MySQLDatabase -xamppPath $xamppPath)) {
        exit 1
    }
    
    # Setup Python environment
    if (-not (Setup-PythonEnvironment)) {
        exit 1
    }
    
    # Migrate data if requested
    if ($MigrateData) {
        if (-not (Migrate-SQLiteData)) {
            Write-Host "⚠️  Data migration failed, but continuing..." -ForegroundColor Yellow
        }
    }
    
    Write-Host "" -ForegroundColor White
    Write-Host "=== Setup Complete! ===" -ForegroundColor Green
    Write-Host ""
    
    # Start the application
    Start-Application
    
}
catch {
    Write-Host "❌ Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
