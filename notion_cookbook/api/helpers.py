import re
from flask import request
from flask_restx import Resource
from functools import wraps
from typing import Callable, Dict, Any

def clean_string(string:str, replace_commas_with:str|None=None):
    '''
    Clean a given string by filtering out characters that are not alphanumeric, spaces, or specific special characters. Optionally, replace commas with a specified character. Return the cleaned string with whitespace trimmed.

    Parameters:
    - string (str): The input string to be cleaned.
    - replace_commas_with (str|None): The character to replace commas with, if specified.

    Returns:
    - str: The cleaned string with specified replacements and trimmed whitespace.
    '''

    if not string:
        return ""

    # Define a regex pattern for allowed characters.
    pattern = re.compile(r"[\w ,.!?'\-½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅐⅛⅜⅝⅞⅑⅒]")
    
    # Create a new array to store the filtered characters.
    filtered_chars = []

    # Iterate through the characters and add only the allowed characters to the filtered string.
    for character in string:
        if pattern.match(character):
            if character == "," and replace_commas_with:
                filtered_chars.append(replace_commas_with) # Use " /"
            else:
                filtered_chars.append(character)

    # Return the filtered string with whitespace trimmed.
    return ''.join(filtered_chars).strip()

# def simulate_internal_call(f: Callable) -> Callable:
#     """
#     Decorator to mark endpoints that can be called internally.
#     Handles both GET and POST methods appropriately.
#     """
#     @wraps(f)
#     def wrapper(*args, **kwargs):
#         # If called internally, use the provided kwargs directly
#         if len(args) > 0 and not isinstance(args[0], Resource):
#             return f(kwargs)
#         # If called via HTTP, use request.args for GET
#         if request.method == 'GET':
#             return f(request.args.to_dict())
#         # For POST requests, use request body
#         return f(request.get_json())
#     return wrapper

def simulate_internal_call(f: Callable) -> Callable:
    """
    Enhanced decorator to mark endpoints that can be called internally.
    Handles:
    - Internal function calls with kwargs
    - GET requests with query parameters
    - GET requests with URL variables
    - POST requests with JSON body
    
    Returns the same response format for both internal and HTTP calls.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Get the instance (self) if this is a method call
        instance = args[0] if args and isinstance(args[0], Resource) else None
        
        # Case 1: Internal call with instance method
        if instance and len(args) > 1:
            return f(instance, args[1])
        
        # Case 2: Internal call without instance (direct dictionary)
        elif not instance and len(args) == 1 and isinstance(args[0], dict):
            # Create a new instance of the class and call the method
            cls = f.__qualname__.split('.')[0]
            instance = globals()[cls]()
            return f(instance, args[0])
        
        # Case 3: HTTP call
        params: Dict[str, Any] = {}
        
        # Add URL variables from view_args (e.g., /api/users/<user_id>)
        if request.view_args:
            params.update(request.view_args)
            
        match request.method:
            case 'GET':
                params.update(request.args.to_dict())
                return f(instance, params)
            
            case 'POST':
                if isinstance(request.get_json(), dict):
                    params.update(request.get_json())
                return f(instance, params)
            
            case _:
                raise ValueError(f"Unsupported HTTP method: {request.method}")
    
    return wrapper