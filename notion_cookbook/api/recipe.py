import os
from typing import Any
import json
from box import Box
import requests
from dotenv import load_dotenv
from flask import request, abort, make_response, redirect, render_template, stream_with_context
from flask.wrappers import Response
from flask_restx import Resource, Namespace
from marshmallow import Schema, fields, ValidationError

from .recipe_handler import NotionRecipeHandler
from .helpers import simulate_internal_call

load_dotenv()

def send_event(data, event=None):
    """Helper function to format SSE data"""
    msg = f"data: {json.dumps(data)}\n\n"
    if event is not None:
        msg = f"event: {event}\n{msg}"
    return msg

recipe_namespace = Namespace("recipe")

@recipe_namespace.route("/")
class RecipeStatus(Resource):
    def get(self):
        return {
            "message": "The RFN namespace is accessible."
        }, 200

# ----- URL PARAMETER SCHEMA -----
class RecipeSchema(Schema):
    url = fields.URL(required=True)  # This alone handles existence and URL format validation
    id = fields.String()

# ----- READ RECIPE DATA -----
@recipe_namespace.route("/analyze")
class AnalyzeRecipeURL(Resource):
    def extract_data(self, recipe_url):
        response = requests.get(
            url = "https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/recipes/extract",
            headers = {
                "x-rapidapi-key": os.getenv("RFN_API_KEY"),
                "x-rapidapi-host": os.getenv("RFN_API_BASE_URL")
            },
            params = {"url": recipe_url}
        )

        if response.ok:
            return Box(response.json())
        
        abort(response)

    def analyze_data(self, recipe_data:Box):
        response = requests.post(
            url = "https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/recipes/analyze",
            params = {
                "language": "en",
                "includeNutrition": "true",
                "includeTaste": "true",
            },
            headers = {
                "x-rapidapi-key": os.getenv("RFN_API_KEY"),
                "x-rapidapi-host": os.getenv("RFN_API_BASE_URL")
            },
            data = json.dumps({
                "title": recipe_data.title,
                "servings": recipe_data.servings,
                "ingredients": [ingredient["original"] for ingredient in recipe_data.extendedIngredients],
                "instructions": recipe_data.instructions,
            }),
            timeout=None
        )

        if response.ok:
            return Box(response.json())
        
        abort(response)

    def run(self, params: dict):
        schema = RecipeSchema()

        try:
            data = Box(schema.load(params))

            # Extract data about the recipe from the webpage
            recipe_data = self.extract_data(data.url)

            # Add only nutrition and taste data to the dict
            # Do not use .update() since that could change the other values in the dict
            analyzed_data = self.analyze_data(recipe_data)
            recipe_data.nutrition = analyzed_data.nutrition
            recipe_data.taste = analyzed_data.taste
            
            return recipe_data, 200
        except ValidationError as err:
            msg = f"Received data: {params}"
            # raise ValidationError(err.messages)
            raise ValidationError(msg)
        # except Exception as e:
        #     return {"error": str(e)}, 500

    def get(self):
        return self.run(request.args.to_dict())

    def post(self):
        data = request.get_json(force=True)

        # Extract data about the recipe from the webpage
        recipe_data = self.extract_data(data.url)

        # Add only nutrition and taste data to the dict
        # Do not use .update() since that could change the other values in the dict
        analyzed_data = self.analyze_data(recipe_data)
        recipe_data.nutrition = analyzed_data.nutrition
        recipe_data.taste = analyzed_data.taste
        
        return recipe_data, 200


# ----- CREATE RECIPE -----
@recipe_namespace.route("/create")
class CreateRecipePage(Resource):
    def get(self) -> Response:
        # Check if this is an HTML request or API request
        if "text/html" in request.headers.get("Accept", ""):
            # Return the loading page template
            return make_response(render_template('loading.html'))

        schema = RecipeSchema()
        data = Box(schema.load(request.args.to_dict()))
        
        # Otherwise handle as SSE stream
        return Response(
            self._process_recipe(data),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
    
    def post(self) -> Response:
        raw_data = Box(request.get_json(force=True))
        data = Box({
            "url": raw_data.data.properties.URL.url,
            "id": raw_data.data.properties.ID.formula.string
        })

        # # Check if this is an HTML request or API request
        # if "text/html" in request.headers.get("Accept", ""):
        #     # Return the loading page template
        #     return render_template('loading.html')

        # Otherwise handle as SSE stream
        return Response(
            self._process_recipe(data),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
        
    def update_page_title(self, message: str, id: str) -> Response:
        headers = {
            "accept": "application/json",
            "Notion-Version": "2022-06-28",
            "content-type": "application/json",
            "Authorization": f"Bearer {os.getenv('NOTION_INTEGRATION_SECRET')}"
        }

        response = requests.patch(
            url=f"https://api.notion.com/v1/pages/{id}",
            headers=headers,
            data=json.dumps({
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [
                            {
                                "type": "text",
                                "text": {
                                    "content": message
                                }
                            }
                        ]
                    },
                }
            })
        )

        return response

    @stream_with_context
    def _process_recipe(self, data):
        try:
            
            # Step 1: Extract recipe data
            yield send_event({"status": "extracting", "message": "Extracting recipe data..."})
            self.update_page_title("Extracting recipe data...", data.id)
            recipe_data, _ = AnalyzeRecipeURL().run(data.to_dict())

            yield send_event({"status": "extracted", "message": "Recipe data extracted successfully"})
            self.update_page_title("Recipe data extracted successfully", data.id)
            
            # Step 2: Process ingredients
            yield send_event({"status": "analyzing", "message": "Analyzing ingredients..."})
            self.update_page_title("Analyzing ingredients...", data.id)
            ingredients = [
                ingredient["nameClean"] if ingredient["nameClean"] else ingredient 
                for ingredient in recipe_data["extendedIngredients"]
            ]

            yield send_event({"status": "analyzed", "message": "Ingredients analyzed successfully"})
            self.update_page_title("Ingredients analyzed successfully", data.id)

            # Step 3: Create the recipe page
            yield send_event({"status": "creating", "message": "Creating recipe page..."})
            self.update_page_title("Creating recipe page...", data.id)
            
            recipe_handler = NotionRecipeHandler(recipe_data)
            recipe_handler.page.parent["database_id"] = os.getenv("NOTION_RECIPE_DATABASE_ID")
            notion_recipe_data = recipe_handler.to_dict()

            headers = {
                "accept": "application/json",
                "Notion-Version": "2022-06-28",
                "content-type": "application/json",
                "Authorization": f"Bearer {os.getenv('NOTION_INTEGRATION_SECRET')}"
            }

            if data.id:
                properties_response = requests.patch(
                    url=f"https://api.notion.com/v1/pages/{data.id}",
                    headers=headers,
                    data=json.dumps({
                        "properties": notion_recipe_data["properties"],
                        'cover': notion_recipe_data["cover"]
                    })
                )

                content_response = requests.patch(
                    url=f"https://api.notion.com/v1/blocks/{data.id}/children",
                    headers=headers,
                    data=json.dumps({"children": notion_recipe_data["children"]})
                )

                url = f"https://www.notion.so/{data.id}"
                success = properties_response.status_code == content_response.status_code == 200
            else:
                response = requests.post(
                    url="https://api.notion.com/v1/pages",
                    headers=headers,
                    data=json.dumps(notion_recipe_data),
                    timeout=None
                )
                url = response.json().get("url")
                success = response.status_code == 200

            if success:
                yield send_event({"status": "created", "message": "Recipe page created successfully"})
                yield send_event({"status": "redirecting", "message": "Redirecting to Notion page...", "url": url})
            else:
                yield send_event({
                    "status": "error",
                    "message": "Failed to create recipe page"
                })

        except ValidationError as err:
            yield send_event({
                "status": "error",
                "message": f"Validation error: {err.messages}"
            })
        except Exception as e:
            yield send_event({
                "status": "error",
                "message": f"Error: {str(e)}"
            })
            self.update_page_title(f"Error: {str(e)}", data.id)
