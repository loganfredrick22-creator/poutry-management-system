# FarmLink XAMPP Quick Start

## 🚀 Quick Setup (5 minutes)

### 1. Install XAMPP
Download and install XAMPP from https://www.apachefriends.org/

### 2. Start XAMPP Services
Open XAMPP Control Panel and start **Apache** and **MySQL**

### 3. Run Setup Script
```powershell
cd "c:\Users\fredr\OneDrive\Desktop\farmlnk project"
.\setup_xampp.ps1
```

### 4. Access Application
Open: http://127.0.0.1:5000/login
- **Username**: admin
- **Password**: admin123

## 📋 Manual Setup (If script fails)

### Step 1: Create Database
1. Go to http://localhost/phpmyadmin
2. Create database: `farmlink`
3. Import: `database/setup_mysql.sql`

### Step 2: Setup Python
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: Configure Environment
Create `.env` file:
```bash
FARMLINK_DB_TYPE=mysql
FARMLINK_MYSQL_HOST=localhost
FARMLINK_MYSQL_USER=root
FARMLINK_MYSQL_PASSWORD=
FARMLINK_MYSQL_DATABASE=farmlink
FARMLINK_EDIT_MODE=all_users
```

### Step 4: Run Application
```powershell
$env:FARMLINK_DB_TYPE="mysql"
python app.py
```

## 🔧 Configuration Options

### Custom MySQL Settings
```powershell
.\setup_xampp.ps1 -MySQLHost "localhost" -MySQLUser "root" -MySQLPassword "your_password"
```

### Migrate Existing SQLite Data
```powershell
.\setup_xampp.ps1 -MigrateData
```

### Custom Application Port
```powershell
.\setup_xampp.ps1 -AppPort 8080
```

## 🌐 Network Access

To access from other computers:
```powershell
.\setup_xampp.ps1 -MySQLHost "0.0.0.0"
```

Then access from other devices: `http://YOUR_IP:5000/login`

## 📁 File Structure

```
farmlnk project/
├── database/
│   ├── setup_mysql.sql          # MySQL database schema
│   └── migrate_sqlite_to_mysql.py  # Data migration script
├── templates/                   # HTML templates
├── routes/                      # Flask routes
├── config.py                    # Configuration settings
├── app.py                       # Main application
├── requirements.txt             # Python dependencies
├── setup_xampp.ps1             # Automated setup script
├── run.ps1                     # Original run script
└── .env.example                # Environment variables template
```

## 🛠️ Troubleshooting

### MySQL Connection Error
- Ensure MySQL is running in XAMPP
- Check credentials in .env file
- Verify database exists in phpMyAdmin

### Python Module Errors
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Port Already in Use
```powershell
.\setup_xampp.ps1 -AppPort 5001
```

## 📚 Documentation

- **Full Guide**: `XAMPP_DEPLOYMENT.md`
- **MySQL Setup**: `MYSQL_SETUP.md`
- **Configuration**: `.env.example`

## 🔒 Security Notes

- Change admin password after first login
- Use strong MySQL password in production
- Enable HTTPS for production deployment
- Regular database backups recommended
