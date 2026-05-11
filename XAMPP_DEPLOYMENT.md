# FarmLink XAMPP Deployment Guide

This guide shows how to deploy FarmLink on XAMPP with MySQL database.

## Prerequisites

1. **XAMPP** installed (https://www.apachefriends.org/)
2. **Python 3.8+** installed
3. **FarmLink project files**

## Step 1: Install XAMPP

1. Download XAMPP from https://www.apachefriends.org/
2. Run the installer (choose default settings)
3. Start XAMPP Control Panel
4. Start **Apache** and **MySQL** services

## Step 2: Configure MySQL Database

### Option A: Using phpMyAdmin (Recommended)

1. Open your browser and go to: http://localhost/phpmyadmin
2. Click **"New"** in the left sidebar
3. Enter database name: `farmlink`
4. Click **"Create"**
5. Click **"Import"** tab
6. Choose file: `database/setup_mysql.sql`
7. Click **"Go"** to execute

### Option B: Using MySQL Command Line

1. Open XAMPP Shell (from XAMPP Control Panel)
2. Run these commands:

```bash
mysql -u root -p
```

Enter password (default: empty, just press Enter)

```sql
SOURCE database/setup_mysql.sql;
EXIT;
```

## Step 3: Configure Python Environment

### 3.1 Install Python Dependencies

```powershell
# Navigate to project directory
cd "c:\Users\fredr\OneDrive\Desktop\farmlnk project"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3.2 Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration for XAMPP
FARMLINK_DB_TYPE=mysql
FARMLINK_MYSQL_HOST=localhost
FARMLINK_MYSQL_PORT=3306
FARMLINK_MYSQL_USER=root
FARMLINK_MYSQL_PASSWORD=
FARMLINK_MYSQL_DATABASE=farmlink

# Access Control (optional - for hosting)
FARMLINK_EDIT_MODE=all_users
FARMLINK_ENABLE_EDITING_FOR_ALL=true

# Security
FARMLINK_SECRET_KEY=your-secret-key-change-this
```

## Step 4: Migrate Existing Data (Optional)

If you have existing SQLite data:

```powershell
# Activate virtual environment first
.venv\Scripts\Activate.ps1

# Run migration script
python database/migrate_sqlite_to_mysql.py
```

## Step 5: Run the Application

### Method A: Using Run Script (Recommended)

```powershell
.\run.ps1
```

### Method B: Manual Start

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Set environment variables
$env:FARMLINK_DB_TYPE="mysql"
$env:FARMLINK_MYSQL_HOST="localhost"
$env:FARMLINK_MYSQL_USER="root"
$env:FARMLINK_MYSQL_PASSWORD=""
$env:FARMLINK_MYSQL_DATABASE="farmlink"

# Run application
python app.py
```

## Step 6: Access the Application

Open your browser and go to:
- **URL**: http://127.0.0.1:5000/login
- **Username**: admin
- **Password**: admin123

## XAMPP Configuration Tips

### MySQL Port Configuration

If MySQL uses a different port:

1. Open XAMPP Control Panel
2. Click **"Config"** next to MySQL
3. Select **"my.ini"**
4. Find and modify the port:
   ```ini
   port = 3306
   ```
5. Restart MySQL service

### Apache Configuration (Optional)

To serve through Apache instead of Flask dev server:

1. Open Apache config (`httpd.conf`)
2. Enable mod_proxy and mod_proxy_http
3. Add this configuration:
   ```apache
   ProxyPreserveHost On
   ProxyPass /farmlink http://127.0.0.1:5000/
   ProxyPassReverse /farmlink http://127.0.0.1:5000/
   ```
4. Restart Apache

### Database Backup

To backup your farmlink database:

```bash
# Using XAMPP Shell
mysqldump -u root -p farmlink > backup.sql
```

To restore:

```bash
mysql -u root -p farmlink < backup.sql
```

## Troubleshooting

### Common Issues

#### 1. MySQL Connection Error
```
Error: Can't connect to MySQL server
```
**Solution**: 
- Ensure MySQL service is running in XAMPP
- Check if port 3306 is available
- Verify credentials in .env file

#### 2. Database Not Found
```
Error: Unknown database 'farmlink'
```
**Solution**:
- Run the setup_mysql.sql script
- Check database name in phpMyAdmin

#### 3. Python Module Errors
```
ModuleNotFoundError: No module named 'PyMySQL'
```
**Solution**:
- Activate virtual environment
- Run: `pip install -r requirements.txt`

#### 4. Port Already in Use
```
Error: Port 5000 is already in use
```
**Solution**:
- Change port in app.py: `app.run(debug=True, host="127.0.0.1", port=5001)`
- Or kill the process using port 5000

### Access from Other Computers

To access from other devices on your network:

1. **Update host binding**:
   ```python
   app.run(debug=True, host="0.0.0.0", port=5000)
   ```

2. **Configure Windows Firewall**:
   - Allow Python through Windows Firewall
   - Open port 5000

3. **Find your IP**:
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" (usually 192.168.x.x)

4. **Access from other devices**:
   ```
   http://YOUR_IP:5000/login
   ```

## Security Considerations

### Production Deployment

1. **Change default passwords**:
   - Update admin user password in the application
   - Set MySQL root password

2. **Use dedicated database user**:
   ```sql
   CREATE USER 'farmlink_app'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON farmlink.* TO 'farmlink_app'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **Enable HTTPS**:
   - Use reverse proxy with SSL
   - Configure Apache with SSL certificates

4. **Regular backups**:
   - Schedule automated MySQL backups
   - Backup application files

## Performance Optimization

### MySQL Optimization

1. **Add indexes** (already included in setup script)
2. **Configure MySQL cache**:
   ```ini
   [mysqld]
   innodb_buffer_pool_size = 256M
   query_cache_size = 32M
   ```
3. **Monitor performance** using phpMyAdmin

### Application Optimization

1. **Use production server** (Gunicorn/uWSGI) instead of Flask dev server
2. **Enable caching** for frequently accessed data
3. **Optimize database queries**

## Maintenance

### Regular Tasks

1. **Weekly**: Database backups
2. **Monthly**: Update Python dependencies
3. **Quarterly**: Review security settings
4. **Annually**: Major updates and maintenance

### Monitoring

- Monitor XAMPP service status
- Check application logs
- Monitor database performance
- Review user activity logs
