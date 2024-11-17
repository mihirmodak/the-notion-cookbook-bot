"""
Health Check System
==================

A comprehensive health monitoring system for Flask web applications that provides
detailed system metrics and external service monitoring with authentication support.

This module provides a flexible and extensible health check system that monitors:
- System resources (CPU, memory, disk, network)
- Process information
- External service availability
- Authentication-protected endpoints

Features
--------
- System metrics monitoring
- External service health checks with multiple authentication methods
- Customizable logging
- Flask integration
- Detailed error reporting
- Response time monitoring

Classes
-------
- HealthCheck: Main health check system
- ExternalService: Configuration for external service monitoring
- ServiceAuth: Authentication configuration
- SystemMetrics: System metrics data container
- AuthType: Authentication type enumeration

Example Usage
------------

Basic Setup:
-----------
```python
from flask import Flask
from health_check import HealthCheck, ExternalService, ServiceAuth, AuthType

# Initialize Flask app
app = Flask(__name__)

# Create health checker instance
health_checker = HealthCheck(
    app_name="MyApp",
    version="1.0.0"
)

# Setup health check route
setup_health_check(app, health_checker)
```

External Service Monitoring:
--------------------------
```python
# Configure external services with different auth types
auth_service = ExternalService(
    name="auth",
    url="https://api.authservice.com/v1/health",
    auth=ServiceAuth(
        auth_type=AuthType.BEARER,
        key=os.getenv("AUTH_SERVICE_API_KEY")
    ),
    headers={
        "Notion-Version": "2022-06-28"
    }
)

api_service = ExternalService(
    name="external_api",
    url="https://api.example.com/health",
    auth=ServiceAuth(
        auth_type=AuthType.API_KEY,
        key=os.getenv("API_KEY"),
        header_name="X-API-Key"
    ),
    timeout=10,
    expected_status=200
)

db_service = ExternalService(
    name="database",
    url="https://db.example.com/health",
    auth=ServiceAuth(
        auth_type=AuthType.BASIC,
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
)

# Add services to health checker
health_checker.add_external_service(auth_service)
health_checker.add_external_service(api_service)
health_checker.add_external_service(db_service)
```

Complete Example:
---------------
```
import os
from flask import Flask
from health_check import (
    HealthCheck,
    ExternalService,
    ServiceAuth,
    AuthType,
    setup_health_check
)


# Initialize Flask app
app = Flask(__name__)

@app.route("/health")
def health_check():
    # Initialize health checker
    health_checker = HealthCheck(
        app_name="MyWebApp",
        version="1.0.0"
    )

    # Configure external services
    services = [
        ExternalService(
            name="external_api",
            url="https://api.example.com/health",
            auth=ServiceAuth(
                auth_type=AuthType.API_KEY,
                key=os.getenv("API_KEY"),
                header_name="X-API-Key"
            ),
            timeout=10,
            expected_status=200
        ),
        ExternalService(
            name="database",
            url="https://db.example.com/health",
            auth=ServiceAuth(
                auth_type=AuthType.BASIC,
                username=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
        )
    ]

    # Add services to health checker
    for service in services:
        health_checker.add_external_service(service)

    health_status = health_checker.run_health_check()
    status_code = 200 if health_status["status"] == "healthy" else 500
    return jsonify(health_status), status_code
```
    
Response Format:
--------------
The health check endpoint (/health) returns a JSON response with the following structure:

```
{
    "status": "healthy",
    "timestamp": "2024-11-07T12:00:00.000Z",
    "app": {
        "name": "MyWebApp",
        "version": "1.0.0",
        "uptime_seconds": 3600
    },
    "system": {
        "platform": "Linux-5.4.0-x86_64",
        "python_version": "3.9.5",
        "hostname": "web-server",
        "ip_address": "10.0.0.1",
        "cpu_cores": 4,
        "cpu_threads": 8
    },
    "metrics": {
        "cpu_usage": [45.2, 32.1, 28.7, 39.4],
        "memory_usage": {
            "total_gb": 16.0,
            "available_gb": 8.5,
            "used_gb": 7.5,
            "usage_percent": 47.0,
            "swap_total_gb": 4.0,
            "swap_used_gb": 0.5,
            "swap_percent": 12.5
        },
        "disk_usage": {
            "/": {
                "total_gb": 256.0,
                "used_gb": 128.0,
                "free_gb": 128.0,
                "usage_percent": 50.0
            }
        },
        "network_stats": {
            "bytes_sent_mb": 1024.5,
            "bytes_recv_mb": 2048.7,
            "packets_sent": 1000000,
            "packets_recv": 2000000,
            "errin": 0,
            "errout": 0,
            "dropin": 0,
            "dropout": 0
        },
        "process_info": {
            "pid": 1234,
            "cpu_percent": 2.5,
            "memory_percent": 1.8,
            "threads": 4,
            "open_files": 7,
            "connections": 23
        }
    },
    "external_services": {
        "external_api": {
            "status": "up",
            "response_time_ms": 245.67,
            "status_code": 200
        },
        "database": {
            "status": "up",
            "response_time_ms": 189.32,
            "status_code": 200
        }
    }
}
```

Configuration Options:
-------------------
AuthType:
- BEARER: Bearer token authentication
- API_KEY: API key authentication
- BASIC: Basic authentication
- NONE: No authentication

ExternalService:
- name: Service identifier
- url: Health check endpoint URL
- auth: ServiceAuth configuration
- timeout: Request timeout in seconds (default: 5)
- expected_status: Expected HTTP status code (default: 200)
- headers: Additional HTTP headers

ServiceAuth:
- auth_type: AuthType enum value
- key: API key or token
- header_name: Custom header name for API key
- username: Basic auth username
- password: Basic auth password

Dependencies:
-----------
- Flask
- psutil
- requests
- python-dotenv (recommended for environment variables)

Installation:
------------
1. Install required packages:
   pip install flask psutil requests python-dotenv

2. Import the module:
   from health_check import HealthCheck, setup_health_check

Security Notes:
-------------
1. Always use environment variables for sensitive credentials
2. Restrict access to the health check endpoint in production
3. Be careful with logging to avoid exposing sensitive information
4. Consider rate limiting the health check endpoint
5. Review the exposed metrics for sensitive information

Best Practices:
-------------
1. Set appropriate timeouts for external service checks
2. Implement proper error handling for failed checks
3. Monitor and rotate logs regularly
4. Use secure connections (HTTPS) for external service checks
5. Implement authentication for the health check endpoint in production
"""

import importlib.metadata
import psutil
import datetime
import platform
import sys
import socket
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging
import time
from enum import Enum

class AuthType(Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    NONE = "none"

@dataclass
class ServiceAuth:
    auth_type: AuthType
    key: Optional[str] = None
    header_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class ExternalService:
    name: str
    url: str
    auth: ServiceAuth
    timeout: int = 5
    expected_status: int = 200
    headers: Optional[Dict[str, str]] = None

    def get_headers(self) -> Dict[str, str]:
        headers = self.headers or {}
        
        if self.auth.auth_type == AuthType.BEARER:
            headers['Authorization'] = f'Bearer {self.auth.key}'
        elif self.auth.auth_type == AuthType.API_KEY:
            headers[self.auth.header_name or 'X-API-Key'] = self.auth.key
            
        return headers

@dataclass
class SystemMetrics:
    cpu_usage: float
    memory_usage: Dict[str, float]
    disk_usage: Dict[str, float]
    network_stats: Dict[str, float]
    process_info: Dict[str, Any]
    load_average: tuple
    uptime: float

class HealthCheck:
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.start_time = time.time()
        self.logger = self._setup_logging()
        self.external_services: List[ExternalService] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for health checks"""
        logger = logging.getLogger('healthcheck')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('healthcheck.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger

    def add_external_service(self, service: ExternalService) -> None:
        """Add an external service to monitor"""
        self.external_services.append(service)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True)
        }
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get detailed memory usage statistics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "usage_percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent
        }
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage for all mounted partitions"""
        disk_info = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.mountpoint] = {
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_percent": usage.percent
                }
            except PermissionError:
                continue
        return disk_info
    
    def get_network_stats(self) -> Dict[str, float]:
        """Get network statistics"""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
            "dropin": net_io.dropin,
            "dropout": net_io.dropout
        }
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about the current process"""
        process = psutil.Process()
        return {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    
    def check_external_services(self) -> Dict[str, Dict[str, Any]]:
        """Check connectivity to external services with authentication"""
        results = {}
        
        for service in self.external_services:
            try:
                start_time = time.time()
                headers = service.get_headers()
                
                # Handle different auth types
                auth = None
                match service.auth.auth_type:
                    case AuthType.BASIC:
                        auth = (service.auth.username, service.auth.password)
                    case AuthType.BEARER:
                        headers["Authorization"] = f"Bearer {service.auth.key}"
                
                response = requests.get(
                    service.url,
                    headers=headers,
                    auth=auth,
                    timeout=service.timeout
                )
                
                response_time = round((time.time() - start_time) * 1000, 2)  # in ms

                service_ok = response.status_code == service.expected_status
                results[service.name] = {
                    "status": "up" if service_ok else "error",
                    "response_time_ms": response_time,
                    "status_code": response.status_code,
                    "message": response.json() if not service_ok else f"The service `{service.name}` is accessible."
                }
                
                # Log successful health check
                self.logger.info(f"Health check for {service.name} completed successfully")
                
            except requests.RequestException as e:
                error_message = str(e)
                results[service.name] = {
                    "status": "down",
                    "error": error_message
                }
                # Log failed health check
                self.logger.error(f"Health check for {service.name} failed: {error_message}")
                
        return results
    
    def get_system_metrics(self) -> SystemMetrics:
        """Collect all system metrics"""
        return SystemMetrics(
            cpu_usage=psutil.cpu_percent(interval=1, percpu=True),
            memory_usage=self.get_memory_usage(),
            disk_usage=self.get_disk_usage(),
            network_stats=self.get_network_stats(),
            process_info=self.get_process_info(),
            load_average=psutil.getloadavg(),
            uptime=time.time() - self.start_time
        )
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run a comprehensive health check"""
        try:
            metrics = self.get_system_metrics()
            
            health_status = {
                "status": "healthy",
                "timestamp": datetime.datetime.now().isoformat(),
                "app": {
                    "name": self.app_name,
                    "version": importlib.metadata.version(self.app_name),
                    "uptime_seconds": metrics.uptime
                },
                "system": self.get_system_info(),
                "metrics": asdict(metrics)
            }
            
            # Add external service checks
            if self.external_services:
                health_status["external_services"] = self.check_external_services()
            
            # Log the health check
            self.logger.info(f"Health check completed successfully")
            
            return health_status
            
        except Exception as e:
            error_status = {
                "status": "error",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": str(e)
            }
            self.logger.error(f"Health check failed: {str(e)}")
            return error_status
