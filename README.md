# The Notion Cookbook Bot

A Flask-based web application that helps manage recipes in Notion. This application provides APIs to analyze recipes, manage ingredients, and handle cuisine classifications and integrates those capabilities with Notion.

## Features

- **Recipe Management**: Analyze and create recipe pages in Notion with structured data
- **Ingredient Database**: Track and categorize ingredients with automatic classification
- **Cuisine Classification**: Automatically classify recipes based on ingredients and title
- **Health Monitoring**: Comprehensive system health checks for all integrated services
- **API Documentation**: Interactive API documentation with Swagger UI

## Prerequisites

- Python >= 3.11
- Notion API Integration
- Spoonacular Recipe-Food-Nutrition API Key
- RapidAPI Account

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
NOTION_INTEGRATION_SECRET=your_notion_secret
NOTION_RECIPE_DATABASE_ID=your_recipe_database_id
NOTION_INGREDIENT_DATABASE_ID=your_ingredient_database_id
NOTION_CUISINE_DATABASE_ID=your_cuisine_database_id
RFN_API_KEY=your_rapidapi_key
RFN_API_BASE_URL=spoonacular-recipe-food-nutrition-v1.p.rapidapi.com
```

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
notion_cookbook/
├── api/
│   ├── __init__.py
│   ├── recipe.py          # Recipe-related endpoints
│   ├── recipe_handler.py  # Notion recipe page handler
│   ├── ingredient.py      # Ingredient management
│   ├── cuisine.py         # Cuisine classification
│   └── helpers.py         # Utility functions
├── server_health.py       # Health monitoring system
└── notion_cookbook.py     # Main application file
```

## API Endpoints

### Recipe Endpoints

- `GET /recipe/`: Check recipe API status
- `GET /recipe/analyze`: Analyze a recipe from a URL
- `GET /recipe/create`: Create a recipe page in Notion

### Ingredient Endpoints

- `GET /ingredient/status`: Check ingredient API status
- `GET /ingredient/create`: Create a new ingredient
- `GET /ingredient/<name>`: Search for an ingredient

### Cuisine Endpoints

- `GET /cuisine/classify`: Classify cuisine based on ingredients and title
- `GET /cuisine/<name>`: Search for a cuisine
- `GET /cuisine/create`: Create a new cuisine entry

### Health Check

- `GET /health`: Get comprehensive system health status
- `GET /`: Basic application status check

## Health Monitoring

The application includes a robust health monitoring system that tracks:

- System resources (CPU, memory, disk, network)
- External service availability
- API response times
- Authentication status

## Data Models

### Recipe Page Structure

- Title and URL
- Ingredients (with relations to ingredient database)
- Course type and servings
- Nutritional information
- Preparation, cooking, and total time
- Cuisine classification
- Tags (dietary restrictions, health markers)

### Notion Integration

The application uses Notion's API to:
- Create and update pages
- Manage database relations
- Handle rich text and multi-select properties
- Manage cover images and icons

## Error Handling

The application implements comprehensive error handling:
- Input validation using Marshmallow schemas
- Detailed error responses with stack traces in development
- HTTP status code mapping
- External service error handling

## Development

To run the application in development mode:

```bash
python notion_cookbook.py
```

The application will start on `http://localhost:5000` with debug mode enabled.

## API Documentation

Access the Swagger UI documentation at `/api/doc` when running the application locally.

## Security Features

- Environment variable based configuration
- Bearer token authentication for Notion API
- API key authentication for Spoonacular
- Error message sanitization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the GNU Affero General Public License - see the LICENSE file for details