import os
from typing import Any
import json
from box import Box
import requests
from dotenv import load_dotenv
from flask import request, abort, make_response, redirect
from flask.wrappers import Response
from flask_restx import Resource, Namespace
from marshmallow import Schema, fields, ValidationError
from pprint import pprint

from .recipe_handler import NotionRecipeHandler
from .helpers import simulate_internal_call

load_dotenv()

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

    @simulate_internal_call
    def get(self, params:dict):
        schema = RecipeSchema()

        try:
            data = Box(schema.load(request.args.to_dict()))

            # Extract data about the recipe from the webpage
            recipe_data = self.extract_data(data.url)

            # Add only nutrition and taste data to the dict
            # Do not use .update() since that could change the other values in the dict
            analyzed_data = self.analyze_data(recipe_data)
            recipe_data.nutrition = analyzed_data.nutrition
            recipe_data.taste = analyzed_data.taste
            
            return recipe_data, 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        # except Exception as e:
        #     return {"error": str(e)}, 500


# ----- CREATE RECIPE -----
@recipe_namespace.route("/create")
class CreateRecipePage(Resource):
    def get(self) -> Response:
        schema = RecipeSchema()

        try:
            data = Box(schema.load(request.args.to_dict()))

            recipe_data, _ = AnalyzeRecipeURL().get(data.to_dict())

            pprint([ingredient["nameClean"] if ingredient["nameClean"] else ingredient for ingredient in recipe_data["extendedIngredients"]])

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
                    headers = headers,
                    data = json.dumps({
                        "properties":notion_recipe_data["properties"],
                        'cover': notion_recipe_data["cover"]
                    })
                )

                content_response = requests.patch(
                    url=f"https://api.notion.com/v1/blocks/{data.id}/children",
                    headers = headers,
                    data = json.dumps({"children": notion_recipe_data["children"]})
                )

                response = make_response(({
                    "properties": properties_response.json(),
                    "content": content_response.json()
                }, 200 if properties_response.status_code == content_response.status_code == 200 else 500))
                url = f"https://www.notion.so/{data.id}"
            else:
                response = requests.post(
                    url = "https://api.notion.com/v1/pages",
                    headers = headers,
                    data = json.dumps(notion_recipe_data),
                    timeout = None
                )
                url = response["url"]

            if response.status_code == 200:
                return redirect(url)
            return make_response(({
                "function": "CreateRecipePage.get",
                "response": response.json
            }, response.status_code))

        except ValidationError as err:
            return {"errors": err.messages}, 400
        # except Exception as e:
        #     return {"error": str(e)}, 500
