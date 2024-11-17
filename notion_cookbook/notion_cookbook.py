import importlib.metadata
import os
import socket
import traceback
from flask import Flask, Blueprint, request, jsonify
from flask_restx import Api
from dotenv import load_dotenv
load_dotenv()

# from web.views import site_blueprint
from .server_health import HealthCheck, ExternalService, ServiceAuth, AuthType
from .api.ingredient import ingredient_namespace
from .api.recipe import recipe_namespace
from .api.cuisine import cuisine_namespace

app = Flask("notion_cookbook")
app.config['PROPAGATE_EXCEPTIONS'] = True # Enable detailed error messages

@app.route("/")
def main():
    # Enhanced response with debug information
    return jsonify({
        "status": "success",
        "message": "The app is accessible",
        "server_info": {
            "hostname": socket.gethostname(),
            "ip": socket.gethostbyname(socket.gethostname())
        }
    }), 200

@app.route("/health")
def health_check():

    health_checker = HealthCheck(
        app_name = "notion_cookbook"
    )

    # Configure your services
    services = [
        ExternalService(
            name="Notion Recipe Database",
            url=f"https://api.notion.com/v1/databases/{os.getenv('NOTION_RECIPE_DATABASE_ID')}",
            auth=ServiceAuth(
                auth_type=AuthType.BEARER,
                key=os.getenv("NOTION_INTEGRATION_SECRET")
            ),
            headers={
                "Notion-Version": "2022-06-28"
            }
        ),
        ExternalService(
            name="Notion Ingredient Database",
            url=f"https://api.notion.com/v1/databases/{os.getenv('NOTION_INGREDIENT_DATABASE_ID')}",
            auth=ServiceAuth(
                auth_type=AuthType.BEARER,
                key=os.getenv("NOTION_INTEGRATION_SECRET")
            ),
            headers={
                "Notion-Version": "2022-06-28"
            }
        ),
        ExternalService(
            name="Notion Cuisine Database",
            url=f"https://api.notion.com/v1/databases/{os.getenv('NOTION_CUISINE_DATABASE_ID')}",
            auth=ServiceAuth(
                auth_type=AuthType.BEARER,
                key=os.getenv("NOTION_INTEGRATION_SECRET")
            ),
            headers={
                "Notion-Version": "2022-06-28"
            }
        ),
        ExternalService(
            name="Spoonacular Recipe-Food-Nutrition API",
            url="https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/food/jokes/random",
            auth=ServiceAuth(
                auth_type=AuthType.API_KEY,
                key=os.getenv("RFN_API_KEY"),
                header_name="X-RapidAPI-Key"
            )
        )
    ]

    for service in services:
        health_checker.add_external_service(service)
    
    health_status = health_checker.run_health_check()
    status_code = 200 if health_status["status"] == "healthy" else 500
    return jsonify(health_status), status_code

@app.errorhandler(Exception)
def handle_error(error):
    return jsonify({
        "message": str(error),
        "type": error.__class__.__name__,
        "traceback": traceback.format_exception(error)
    }), 500

# ----- API -----
api_blueprint = Blueprint("api", "The Cookbook Bot") # url_prefix="/api/v1"
api = Api(
    api_blueprint,
    version="1.0",
    title="The Cookbook Bot API",
    description="Internal API for The Cookbook Bot",
    doc="/doc"
)
api.add_namespace(ingredient_namespace)
api.add_namespace(recipe_namespace)
api.add_namespace(cuisine_namespace)

# app.register_blueprint(site_blueprint)
app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, load_dotenv=True)