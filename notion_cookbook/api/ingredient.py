import os
import json
import jsonschema
from box import Box
import urllib
import requests
from marshmallow import Schema, fields, validates_schema, ValidationError
from flask import request, make_response, jsonify
from flask.wrappers import Response
from flask_restx import Resource, Namespace

from .helpers import clean_string, simulate_internal_call

ingredient_namespace = Namespace("ingredient")

@ingredient_namespace.route("/status")
class IngredientStatus(Resource):
    def get(self):
        return {
            "message": "The Notion namespace is accessible."
        }, 200


# ----- CREATE -----
class IngredientSchema(Schema):
    name = fields.String(required=True)
    category = fields.String(required=False)


@ingredient_namespace.route("/create")
class CreateIngredient(Resource):
    @simulate_internal_call
    def get(self, params:dict) -> Response:

        # get URL parameters
        schema = IngredientSchema()
        data = Box(schema.load(params))

        # convert categories to a list
        if hasattr(data, 'category') and data.category:
            ingredient_categories = [{
                "name": clean_string(token).title(),
                "color": "default"
            } for token in data.category.split(";")]
        else:
            ingredient_categories = [{
                "name": "General",
                "color": "default"
            }]

        # send data to Notion
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
                    "database_id": os.getenv("NOTION_INGREDIENT_DATABASE_ID")
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
                    "Category": {
                        "multi_select": ingredient_categories
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

        return make_response(response.json())


# ----- READ -----
@ingredient_namespace.route("/<string:name>")
class SearchForIngredient(Resource):
    def get(self, name:str) -> Response:
        name = urllib.parse.unquote(name)

        notion_response = requests.request(
            method = "POST",
            url = f"https://api.notion.com/v1/databases/{os.getenv('NOTION_INGREDIENT_DATABASE_ID')}/query",
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
