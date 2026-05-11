import os
from typing import ClassVar


class Config:
    """Application configuration settings."""
    
    # Database settings
    SECRET_KEY: str = os.environ.get("FARMLINK_SECRET_KEY", "dev-secret-change-me")
    
    # Database configuration - supports both SQLite and MySQL
    DB_TYPE: str = os.environ.get("FARMLINK_DB_TYPE", "sqlite")  # Options: "sqlite", "mysql"
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Generate database URI based on DB_TYPE."""
        if self.DB_TYPE == "mysql":
            # MySQL connection
            host = os.environ.get("FARMLINK_MYSQL_HOST", "localhost")
            port = os.environ.get("FARMLINK_MYSQL_PORT", "3306")
            user = os.environ.get("FARMLINK_MYSQL_USER", "farmlink")
            password = os.environ.get("FARMLINK_MYSQL_PASSWORD", "")
            database = os.environ.get("FARMLINK_MYSQL_DATABASE", "farmlink")
            
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        else:
            # Default SQLite
            return "sqlite:///farmlink.db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    
    # Access control settings
    # Set to 'True' to enable editing for all authenticated users
    # Set to 'False' to restrict editing to admin users only
    ENABLE_EDITING_FOR_ALL_USERS: bool = os.environ.get("FARMLINK_ENABLE_EDITING_FOR_ALL", "false").lower() == "true"
    
    # Alternative: Set to 'admin_only' to restrict editing to admins only
    # Set to 'all_users' to allow all authenticated users to edit
    EDIT_MODE: str = os.environ.get("FARMLINK_EDIT_MODE", "admin_only")  # Options: "admin_only", "all_users"
    
    @classmethod
    def is_editing_enabled(cls, user_role: str) -> bool:
        """Check if editing is enabled for a user with the given role."""
        if cls.EDIT_MODE == "all_users":
            return True
        elif cls.EDIT_MODE == "admin_only":
            return user_role == "admin"
        else:
            # Fallback to the boolean setting
            return cls.ENABLE_EDITING_FOR_ALL_USERS or user_role == "admin"


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False


# Configuration mapping
config_by_name: ClassVar = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
