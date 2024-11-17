import os
from typing import Any
import json
import requests
import urllib
from flask import request, make_response, jsonify
from flask_restx import Resource, Namespace
from flask.wrappers import Response
from marshmallow import Schema, fields, ValidationError
from box import Box

from dotenv import load_dotenv
load_dotenv()

from .helpers import simulate_internal_call

cuisine_namespace = Namespace("cuisine")

class CuisineClassificationSchema(Schema):
    title = fields.String(required=True)
    ingredients = fields.String(required=True)

class CuisineCreationSchema(Schema):
    name = fields.String(required=True)
    type = fields.String(required=True)
    # do not include cover since there is no way to send a file through a GET method

@cuisine_namespace.route("/classify")
class ClassifyCuisine(Resource):
    @simulate_internal_call
    def get(self, params:dict) -> Response:
        schema = CuisineClassificationSchema()

        try:
            data = Box(schema.load(params))

            # Extract data about the recipe from the webpage
            response = requests.post(
                url = "https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/recipes/cuisine",
                headers = {
                    "x-rapidapi-key": "8c6a756049msh45e60c3774be490p1eb511jsn4e0d4e0cf769",
                    "x-rapidapi-host": "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com",
                    "Content-Type": "application/json"
                },
                data = {
                    "ingredientList": data.ingredients.split(';'),
                    "title": data.title
                }
            )

            return make_response((response.json(), response.status_code))
            
        except ValidationError as err:
            return make_response(({"errors": err.messages}, 400))

@cuisine_namespace.route("/<string:name>")
class SearchForCuisine(Resource):
    def get(self, name:str) -> Response:
        name = urllib.parse.unquote(name)

        notion_response = requests.request(
            method = "POST",
            url = f"https://api.notion.com/v1/databases/{os.getenv('NOTION_CUISINE_DATABASE_ID')}/query",
            headers = {
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('NOTION_INTEGRATION_SECRET')}",
            },
            data = json.dumps({
                "filter": {
                    "property": "Name",
                    "rich_text": {
                        "equals": name
                    }
                }
            })
        )

        results = []
        if "results" in notion_response.json():
            results = notion_response.json()["results"]

        # Handle both success and error cases by converting to JSON
        if notion_response.ok:
            if len(results) > 0:
                return make_response(jsonify(results[0]), notion_response.status_code)
            else:
                return make_response(jsonify({"id":None, "query": name, "response": notion_response.json()}), notion_response.status_code)
        else:
            # Return the error response in a JSON format
            return make_response(
                jsonify({
                    "error": notion_response.reason,
                    "status_code": notion_response.status_code,
                    "detail": notion_response.json() if notion_response.content else notion_response.text
                }), 
                notion_response.status_code
            )


@cuisine_namespace.route("/create")
class CreateCuisine(Resource):
    @simulate_internal_call
    def get(self, params:dict) -> Response:
        schema = CuisineCreationSchema()

        try:
            data = Box(schema.load(params))

            response = requests.request(
                method = "POST",
                url = "https://api.notion.com/v1/pages",
                headers = {
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('NOTION_INTEGRATION_SECRET')}",
                },
                data = json.dumps({
                    "parent": {
                        "database_id": os.getenv("NOTION_CUISINE_DATABASE_ID")
                    },
                    "properties": {
                        "Name": {
                            "type": "title",
                            "title": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": data.name
                                    }
                                }
                            ]
                        },
                        "Type": {
                            "select": data.type
                        }
                    },
                    "icon": {
                        "type": "external",
                        "external": {
                            "url": "https://www.notion.so/icons/grocery_gray.svg"
                        }
                    }
                })
            )

            return make_response((response.json(), response.status_code))
        except ValidationError as err:
            return make_response(({"errors": err.messages}, 400))