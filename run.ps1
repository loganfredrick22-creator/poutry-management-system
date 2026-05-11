$ErrorActionPreference = "Stop"

Write-Host "== FarmLink Poultry runner ==" -ForegroundColor Green

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

if (!(Test-Path ".\.venv")) {
  Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Yellow
  py -3 -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. ".\.venv\Scripts\Activate.ps1"

Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip | Out-Host

Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt | Out-Host

Write-Host "Starting FarmLink server..." -ForegroundColor Green
Write-Host "Open: http://127.0.0.1:5000/login" -ForegroundColor Cyan
Write-Host "Admin: admin / admin123" -ForegroundColor Cyan

# Check configuration
$dbType = $env:FARMLINK_DB_TYPE
$editMode = $env:FARMLINK_EDIT_MODE
$enableEditing = $env:FARMLINK_ENABLE_EDITING_FOR_ALL

Write-Host "Database: $dbType (default: sqlite)" -ForegroundColor Cyan
if ($dbType -eq "mysql") {
    Write-Host "MySQL Configuration:" -ForegroundColor Yellow
    Write-Host "  Host: $($env:FARMLINK_MYSQL_HOST)" -ForegroundColor Gray
    Write-Host "  Port: $($env:FARMLINK_MYSQL_PORT)" -ForegroundColor Gray
    Write-Host "  User: $($env:FARMLINK_MYSQL_USER)" -ForegroundColor Gray
    Write-Host "  Database: $($env:FARMLINK_MYSQL_DATABASE)" -ForegroundColor Gray
    Write-Host "" -ForegroundColor White
    Write-Host "To switch to MySQL:" -ForegroundColor Yellow
    Write-Host "  `$env:FARMLINK_DB_TYPE='mysql'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_HOST='localhost'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_USER='your_user'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_PASSWORD='your_password'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_DATABASE='farmlink'" -ForegroundColor Gray
} else {
    Write-Host "To switch to MySQL:" -ForegroundColor Yellow
    Write-Host "  `$env:FARMLINK_DB_TYPE='mysql'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_HOST='localhost'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_USER='your_user'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_PASSWORD='your_password'" -ForegroundColor Gray
    Write-Host "  `$env:FARMLINK_MYSQL_DATABASE='farmlink'" -ForegroundColor Gray
}

Write-Host "" -ForegroundColor White
if ($editMode -eq "all_users" -or $enableEditing -eq "true") {
    Write-Host "Edit mode: ENABLED for all users" -ForegroundColor Yellow
} else {
    Write-Host "Edit mode: Admin-only (default)" -ForegroundColor Cyan
    Write-Host "To enable editing for all users when hosted elsewhere:" -ForegroundColor Yellow
    Write-Host "  Set FARMLINK_EDIT_MODE=all_users" -ForegroundColor Gray
    Write-Host "  or FARMLINK_ENABLE_EDITING_FOR_ALL=true" -ForegroundColor Gray
}

python app.py

