from dataclasses import dataclass, field, is_dataclass
from typing import List, Optional, Dict, Any
import urllib

from .helpers import clean_string
from .ingredient import SearchForIngredient, CreateIngredient
from .cuisine import ClassifyCuisine, SearchForCuisine, CreateCuisine

# ----- DATACLASSES FOR NOTION TYPES -----
class BaseDataClass:
    def to_dict(self) -> dict[str, Any]:
        """
        Converts a dataclass instance to a dictionary, handling nested dataclasses,
        Optional types, and lists.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the dataclass
        """
        result = {}
        
        for field_name, field_value in self.__class__.__dataclass_fields__.items():
            value = getattr(self, field_name)
            
            # Handle None values
            if value is None:
                result[field_name] = None
                continue
                
            # Handle nested dataclasses
            if is_dataclass(value):
                result[field_name] = value.to_dict()
                continue
                
            # Handle lists
            if isinstance(value, list):
                # Convert list items if they're dataclasses
                result[field_name] = [
                    item.to_dict() if is_dataclass(item) else item
                    for item in value
                ]
                continue
                
            # Handle regular values
            result[field_name] = value
            
        return result

@dataclass
class NotionText(BaseDataClass):
    content: Optional[str] = None
    link: Optional[str] = None

@dataclass
class NotionAnnotations(BaseDataClass):
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    color: str = "default"

@dataclass
class NotionTitleElement(BaseDataClass):
    type: str = "text"
    text: NotionText = field(default_factory=NotionText)
    annotations: NotionAnnotations = field(default_factory=NotionAnnotations)

@dataclass
class NotionTitle(BaseDataClass):
    type: str = "title"
    title: List[NotionTitleElement] = field(default_factory=lambda: [NotionTitleElement()])

@dataclass
class NotionRelation(BaseDataClass):
    type: str = "relation"
    relation: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class NotionMultiSelect(BaseDataClass):
    type: str = "multi_select"
    multi_select: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class NotionNumber(BaseDataClass):
    type: str = "number"
    number: Optional[float] = None

@dataclass
class NotionURL(BaseDataClass):
    type: str = "url"
    url: Optional[str] = None

@dataclass
class NotionCheckbox(BaseDataClass):
    type: str = "checkbox"
    checkbox: bool = False

@dataclass
class NotionFileElement(BaseDataClass):
    name: str
    type: str = "external"
    external: Dict[str, str] = field(default_factory=dict)

@dataclass
class NotionFiles(BaseDataClass):
    type: str = "files"
    files: List[NotionFileElement] = field(default_factory=list)

# ----- ALL THE PROPERTIES FOR A RECIPE PAGE -----
@dataclass
class NotionProperties:
    Name: NotionTitle = field(default_factory=NotionTitle)
    Ingredients: NotionRelation = field(default_factory=NotionRelation)
    URL: NotionURL = field(default_factory=NotionURL)
    Course: NotionMultiSelect = field(default_factory=NotionMultiSelect)
    Servings: NotionNumber = field(default_factory=NotionNumber)
    Calories: NotionNumber = field(default_factory=NotionNumber)
    Protein: NotionNumber = field(default_factory=lambda: NotionNumber(type="number"))
    Prep_Time: NotionNumber = field(default_factory=NotionNumber)
    Cooking_Time: NotionNumber = field(default_factory=NotionNumber)
    Total_Time: NotionNumber = field(default_factory=NotionNumber)
    Favorite: NotionCheckbox = field(default_factory=NotionCheckbox)
    Cuisine: NotionRelation = field(default_factory=NotionRelation)
    CuisineOLD: NotionMultiSelect = field(default_factory=NotionMultiSelect)
    Tags: NotionMultiSelect = field(default_factory=NotionMultiSelect)
    # Cover: NotionFiles = field(default_factory=NotionFiles)

    def to_dict(self) -> dict[str, Any]:
        return {
            "Name": self.Name.to_dict(),
            "Ingredients": self.Ingredients.to_dict(),
            "URL": self.URL.to_dict(),
            "Course": self.Course.to_dict(),
            "Servings": self.Servings.to_dict(),
            "Calories": self.Calories.to_dict(),
            "Protein": self.Protein.to_dict(),
            "Preparation Mins": self.Prep_Time.to_dict(),
            "Cooking Mins": self.Cooking_Time.to_dict(),
            "Total Mins": self.Total_Time.to_dict(),
            "Favorite": self.Favorite.to_dict(),
            "Cuisine": self.Cuisine.to_dict(),
            "Tags": self.Tags.to_dict()
        }

@dataclass
class NotionPage:
    parent: Dict[str, Any] = field(default_factory=lambda: {"database_id": None})
    cover: Dict[str, Any] = field(default_factory=lambda: {
        "type": "external",
        "external": {
            "url": "https://i.imgur.com/1bY0aV1.png"
        }
    })
    icon: Dict[str, Any] = field(default_factory=lambda: {
        "type": "external",
        "external": {
            "url": "https://www.notion.so/icons/bowl-food_gray.svg"
        }
    })
    properties: NotionProperties = field(default_factory=NotionProperties)
    children: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Convert the NotionPage instance to a dictionary format suitable for Notion API.
        
        Returns:
            Dict[str, Any]: A dictionary containing all the NotionPage fields.
            
        Example:
            page = NotionPage()
            page_dict = page.__dict__()
        """
        return {
            "parent": self.parent,
            "cover": self.cover,
            "icon": self.icon,
            "properties": self.properties.to_dict(),
            "children": self.children
        }

# ----- EXTERNAL HANDLER CLASS -----

class NotionRecipeHandler:
    def __init__(self, recipe_data: Optional[dict] = None):
        self.page = NotionPage()
        if recipe_data:
            self._add_properties(recipe_data)
            self._add_content(recipe_data)

    def add_data(self, recipe_data: dict) -> None:
        """Add all recipe data to the Notion page"""
        self._add_properties(recipe_data)
        self._add_content(recipe_data)

    def _add_properties(self, recipe_data: dict) -> None:
        """Add properties to the Notion page from recipe data"""
        # Cover Image
        self.page.cover["external"]["url"] = recipe_data["image"]

        props = self.page.properties

        # Basic properties
        props.Name.title[0].text.content = recipe_data['title']
        props.URL.url = recipe_data['sourceUrl']
        
        # Course
        if recipe_data.get('dishTypes'):
            props.Course.multi_select = [
                {"name": type_.title(), "color": "default"} 
                for type_ in recipe_data['dishTypes']
            ]

        # Servings
        if recipe_data['servings'] != -1:
            props.Servings.number = recipe_data['servings']

        # Nutrition
        for nutrient in recipe_data['nutrition']['nutrients']:
            if nutrient['name'] == 'Calories':
                props.Calories.number = nutrient['amount']
            elif nutrient['name'] == 'Protein':
                props.Protein.number = nutrient['amount']

        # Time
        if recipe_data['preparationMinutes'] != -1:
            props.Prep_Time.number = recipe_data['preparationMinutes']
        if recipe_data['cookingMinutes'] != -1:
            props.Cooking_Time.number = recipe_data['cookingMinutes']
        if recipe_data['readyInMinutes'] != -1:
            props.Total_Time.number = recipe_data['readyInMinutes']

        # Cuisines
        if recipe_data.get('cuisines'):
            props.Cuisine.multi_select = [
                {"name": cuisine, "color": "default"} 
                for cuisine in recipe_data['cuisines']
            ]

        # Tags
        tags = []
        if recipe_data.get('vegetarian'):
            tags.append("Vegetarian")
        if recipe_data.get('vegan'):
            tags.append("Vegan")
        if recipe_data.get('glutenFree'):
            tags.append("Gluten Free")
        if recipe_data.get('veryHealthy'):
            tags.append("Healthy")
        if recipe_data.get('cheap'):
            tags.append("Cheap")
        if recipe_data.get('dairyFree'):
            tags.append("Dairy Free")
        
        if props.Calories.number and props.Protein.number:
            if props.Calories.number / props.Protein.number < 15:
                tags.append("High Protein")
                
        props.Tags.multi_select = [{"name": tag, "color": "default"} for tag in tags]

        # Ingredients
        if recipe_data.get('extendedIngredients'):
            props.Ingredients.relation = [
                {"id": self._get_ingredient_id(ingredient)}
                for ingredient in recipe_data['extendedIngredients']
            ]

        # Cuisines
        props.Cuisine.relation = [{"id": self._get_cuisine_id({
            "title": recipe_data["title"],
            "ingredients": ';'.join([ingredient["nameClean"] for ingredient in recipe_data["extendedIngredients"] if ingredient["nameClean"]])
        })}]

    def _add_content(self, recipe_data: dict) -> None:
        """Add content blocks to the Notion page"""
        content = []
        
        # Add ingredients section
        content.extend([
            self._create_heading3("Ingredients"),
            {"object": "block", "type": "divider", "divider": {}}
        ])
        
        # Add ingredients list
        for ingredient in recipe_data["extendedIngredients"]:
            content.append(self._create_bullet_item(ingredient["original"]))
        
        # Add instructions section
        content.extend([
            self._create_heading3("Instructions"),
            {"object": "block", "type": "divider", "divider": {}}
        ])
        
        # Add instructions
        for instruction in recipe_data["analyzedInstructions"]:
            if not instruction["name"]:
                for step in instruction["steps"]:
                    content.append(self._create_numbered_item(step["step"]))
            else:
                steps = [self._create_numbered_item(step["step"]) 
                        for step in instruction["steps"]]
                content.append(self._create_numbered_item(
                    instruction["name"], 
                    children=steps
                ))

        self.page.children = content

    @staticmethod
    def _create_heading3(text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    @staticmethod
    def _create_bullet_item(text: str) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    @staticmethod
    def _create_numbered_item(text: str, children: List[dict] = None) -> dict:
        item = {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }
        if children:
            item["numbered_list_item"]["children"] = children
        return item

    def _get_ingredient_id(self, ingredient: dict) -> str:
        """Override this method to implement ingredient ID lookup"""
        ingredient_name = clean_string(ingredient["nameClean"]).title()

        ingredient_category = "General"
        if ingredient["aisle"] is not None:
            ingredient_category = clean_string(ingredient["aisle"], replace_commas_with=" /").title()

        found_ingredient = SearchForIngredient().get(ingredient_name)
        ingredient_id = found_ingredient.json["id"]
        if not ingredient_id:
            created_ingredient = CreateIngredient().get({"name":ingredient_name, "category":ingredient_category})
            ingredient_id = created_ingredient.json["id"]

        return ingredient_id

    def _get_cuisine_id(self, recipe_data:dict) -> str:
        try:
            cuisine = ClassifyCuisine().get({
                "ingredients": recipe_data["ingredients"],
                "title": recipe_data["title"]
            }).json["cuisine"]
        except KeyError:
            cuisine = "Unknown"

        cuisine = clean_string(cuisine)

        found_cuisine = SearchForCuisine().get(cuisine)
        cuisine_id = found_cuisine.json["id"]
        if not cuisine_id:
            created_cuisine = CreateCuisine().get({"name": cuisine, "type": "Cuisine"})
            cuisine_id = created_cuisine.json["id"]

        return cuisine_id

        

    def to_dict(self) -> dict:
        """Convert the page to a dictionary for the API request"""
        return self.page.to_dict()

# # Usage example:
# def create_notion_recipe(recipe_data: dict) -> dict:
#     handler = NotionRecipeHandler()
#     handler.add_data(recipe_data)
#     return handler.to_dict()