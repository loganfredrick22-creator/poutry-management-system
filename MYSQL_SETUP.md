# MySQL Setup for FarmLink

This guide shows how to switch from SQLite to MySQL for your FarmLink application.

## Prerequisites

1. MySQL Server installed and running
2. MySQL user with database creation privileges
3. Python environment with required packages

## Quick Setup

### 1. Install MySQL Dependencies
```powershell
pip install PyMySQL cryptography
```

### 2. Create MySQL Database
```sql
-- Connect to MySQL as root/admin user
CREATE DATABASE farmlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'farmlink'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON farmlink.* TO 'farmlink'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Configure Environment Variables

#### Option A: Using Environment Variables (Recommended for hosting)
```powershell
$env:FARMLINK_DB_TYPE="mysql"
$env:FARMLINK_MYSQL_HOST="localhost"
$env:FARMLINK_MYSQL_PORT="3306"
$env:FARMLINK_MYSQL_USER="farmlink"
$env:FARMLINK_MYSQL_PASSWORD="your_secure_password"
$env:FARMLINK_MYSQL_DATABASE="farmlink"
```

#### Option B: Using .env File
Create a `.env` file in your project root:
```bash
FARMLINK_DB_TYPE=mysql
FARMLINK_MYSQL_HOST=localhost
FARMLINK_MYSQL_PORT=3306
FARMLINK_MYSQL_USER=farmlink
FARMLINK_MYSQL_PASSWORD=your_secure_password
FARMLINK_MYSQL_DATABASE=farmlink
```

### 4. Run the Application
```powershell
.\run.ps1
```

The application will automatically:
- Connect to MySQL using the provided credentials
- Create all necessary tables on first run
- Seed the admin user and sample data

## Configuration Options

### Database Connection Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `FARMLINK_DB_TYPE` | `sqlite` | Database type: `sqlite` or `mysql` |
| `FARMLINK_MYSQL_HOST` | `localhost` | MySQL server hostname |
| `FARMLINK_MYSQL_PORT` | `3306` | MySQL server port |
| `FARMLINK_MYSQL_USER` | `farmlink` | MySQL username |
| `FARMLINK_MYSQL_PASSWORD` | `""` | MySQL password |
| `FARMLINK_MYSQL_DATABASE` | `farmlink` | Database name |

### Connection String Format
The application generates MySQL connection strings in this format:
```
mysql+pymysql://user:password@host:port/database
```

## Migration from SQLite to MySQL

If you have existing SQLite data and want to migrate to MySQL:

### Method 1: Fresh Start (Recommended)
1. Set up MySQL as shown above
2. The application will create fresh tables and seed new data
3. Re-enter your data manually

### Method 2: Data Migration (Advanced)
For existing SQLite data migration, you would need to:
1. Export data from SQLite
2. Transform data for MySQL compatibility
3. Import into MySQL tables

*Note: Data migration scripts are not included as this is typically a one-time setup process.*

## Troubleshooting

### Common Issues

#### Connection Error
```
Error: Can't connect to MySQL server
```
**Solution**: Check MySQL server is running and credentials are correct

#### Permission Error
```
Error: Access denied for user
```
**Solution**: Verify MySQL user has proper privileges on the database

#### Database Not Found
```
Error: Unknown database 'farmlink'
```
**Solution**: Create the database first using MySQL commands

### Testing Connection
Test your MySQL connection with this simple Python script:
```python
import pymysql
try:
    conn = pymysql.connect(
        host='localhost',
        user='farmlink',
        password='your_password',
        database='farmlink'
    )
    print("MySQL connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

## Hosting Considerations

When hosting on another computer:

1. **Security**: Use strong passwords and limit database user privileges
2. **Network**: Ensure MySQL server accepts remote connections if needed
3. **Backups**: Set up regular MySQL backups
4. **Performance**: Monitor MySQL performance for production use

## Switching Back to SQLite

To switch back to SQLite:
```powershell
Remove-Item Env:FARMLINK_DB_TYPE
# Or set it explicitly:
$env:FARMLINK_DB_TYPE="sqlite"
```

The application will then use the local `farmlink.db` file again.
