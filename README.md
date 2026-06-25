# FarmLink Poultry Management System

 **AI-Enhanced Flock Management and Bird Identification System**

A comprehensive Flask-based web application for poultry farm management with AI-powered analytics, health monitoring, and bird tracking capabilities.

##  Features

### Core Management
- **Bird Registry**: Track individual birds with leg bands, breeds, and health records
- **Flock Management**: Organize birds into flocks with location and category tracking
- **Health Monitoring**: Record vaccinations, diseases, treatments, and checkups
- **Mortality Tracking**: Log and analyze mortality patterns
- **Growth Monitoring**: Track weight records and growth trends
- **Egg Production**: Monitor and forecast layer productivity

### AI-Powered Analytics
- **Health Scoring**: AI-calculated health scores for each bird
- **Risk Assessment**: Flock-level risk classification and anomaly detection
- **Mortality Prediction**: 14-day mortality probability forecasting
- **Productivity Forecasting**: AI-powered egg production predictions
- **Recommendations**: Intelligent management recommendations

### User Management & Security
- **Role-Based Access**: Admin and user roles with configurable permissions
- **Secure Authentication**: Bcrypt password hashing and session management
- **Audit Logging**: Complete audit trail of all data changes

### Database Support
- **SQLite**: Default database for development and small deployments
- **MySQL**: Production-ready database with full migration support
- **XAMPP Compatible**: Optimized for XAMPP deployment

##  Quick Start

### Option 1: Using XAMPP (Recommended for Windows)
```powershell
# 1. Install XAMPP (https://www.apachefriends.org/)
# 2. Start Apache and MySQL services
# 3. Run automated setup
.\setup_xampp.ps1
```

### Option 2: Local Development
```powershell
# 1. Clone repository
git clone <repository-url>
cd farmlnk-project

# 2. Setup environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Run application
.\run.ps1
```

##  Prerequisites

- **Python 3.8+**
- **MySQL Server** (for production) or **SQLite** (for development)
- **XAMPP** (optional, for Windows deployment)

##  Database Setup

### SQLite (Default)
No setup required - database is created automatically on first run.

### MySQL Production Setup
```bash
# 1. Create database
mysql -u root -p -e "CREATE DATABASE farmlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Import schema
mysql -u root -p farmlink < database/setup_mysql.sql

# 3. Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials
```

### Data Migration
```bash
# Migrate existing SQLite data to MySQL
python database/migrate_sqlite_to_mysql.py
```

##  Configuration

### Environment Variables
```bash
# Database Configuration
FARMLINK_DB_TYPE=mysql                    # Options: sqlite, mysql
FARMLINK_MYSQL_HOST=localhost
FARMLINK_MYSQL_USER=farmlink
FARMLINK_MYSQL_PASSWORD=your_password
FARMLINK_MYSQL_DATABASE=farmlink

# Access Control
FARMLINK_EDIT_MODE=admin_only           # Options: admin_only, all_users
FARMLINK_ENABLE_EDITING_FOR_ALL=false   # Options: true, false

# Security
FARMLINK_SECRET_KEY=your-secret-key
```

### Access Control Modes

- **Admin-Only**: Only admin users can modify data (default)
- **All Users**: All authenticated users can modify data (for hosted deployments)

##  Deployment

### XAMPP Deployment
1. Install XAMPP and start services
2. Run `.\setup_xampp.ps1`
3. Access at http://127.0.0.1:5000/login

### Production Deployment
1. Configure MySQL database
2. Set environment variables
3. Use production WSGI server (Gunicorn/uWSGI)
4. Configure reverse proxy (Apache/Nginx)
5. Enable SSL/HTTPS

##  Project Structure

```
farmlnk-project/
├── app.py                      # Main Flask application
├── config.py                    # Configuration settings
├── decorators.py                # Access control decorators
├── security.py                 # Security utilities
├── utils.py                    # Helper functions
├── ai.py                       # AI analytics and predictions
├── seed.py                     # Database seeding
├── models.py                   # SQLAlchemy models
├── routes/                     # Flask blueprints
│   ├── __init__.py
│   ├── auth.py                 # Authentication routes
│   ├── main.py                 # Main application routes
│   ├── api.py                  # API endpoints
│   └── users.py                # User management
├── templates/                   # Jinja2 templates
├── database/                   # Database setup and migration
│   ├── setup_mysql.sql
│   └── migrate_sqlite_to_mysql.py
├── static/                     # Static assets (CSS, JS, images)
├── instance/                    # Flask instance folder
├── requirements.txt             # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                # Git ignore file
├── run.ps1                   # PowerShell run script
├── setup_xampp.ps1           # XAMPP setup script
└── README.md                 # This file
```

##  Development

### Adding New Features
1. Create models in `models.py`
2. Add routes in appropriate `routes/*.py` file
3. Create templates in `templates/`
4. Update configuration if needed

### Running Tests
```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run application in development mode
python app.py
```

### Database Schema
The application uses the following main entities:
- **Users**: Authentication and role management
- **Flocks**: Group organization
- **Birds**: Individual bird tracking
- **Health Events**: Medical and health records
- **Mortality Logs**: Death tracking
- **Weight Records**: Growth monitoring
- **Egg Production**: Productivity tracking
- **Audit Logs**: Change tracking

##  AI Features

### Health Scoring Algorithm
- Vaccination coverage analysis
- Disease history weighting
- Growth trend evaluation
- Recent health events impact

### Risk Assessment
- Mortality rate analysis (7-day windows)
- Health score aggregation
- Outbreak detection
- Environmental risk factors

### Predictive Analytics
- Mortality probability forecasting
- Egg production predictions
- Growth trend analysis
- Performance benchmarking

##  Security

### Authentication
- Bcrypt password hashing
- Session-based authentication
- CSRF protection
- Secure password policies

### Access Control
- Role-based permissions
- Audit logging
- Configurable edit permissions
- User management interface

##  Documentation

- **[XAMPP_DEPLOYMENT.md](XAMPP_DEPLOYMENT.md)**: Comprehensive XAMPP setup guide
- **[MYSQL_SETUP.md](MYSQL_SETUP.md)**: MySQL configuration and migration
- **[README_XAMPP.md](README_XAMPP.md)**: Quick start guide

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

##  License

This project is licensed under the MIT License - see the LICENSE file for details.

##  Issues & Support

For bug reports and feature requests, please use the GitHub issue tracker.

##  Performance

### Database Optimization
- Indexed queries for fast lookups
- Optimized foreign key relationships
- Connection pooling for production

### Application Performance
- Template caching
- Static asset optimization
- Efficient query patterns

##  Future Features

- Mobile application support
- Advanced reporting dashboards
- Integration with IoT sensors
- Multi-language support
- Cloud deployment options

---

**Default Credentials**: admin / admin123

**First Run**: The application automatically creates an admin user and seeds sample data on first launch.

**Production Deployment**: Remember to change default passwords and use HTTPS in production environments.
