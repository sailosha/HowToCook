import json
from flask import Flask, render_template, url_for, abort, send_from_directory
import os
from pathlib import Path # Import Path

app = Flask(__name__)
# Define the absolute path to the 'dishes' directory for send_from_directory
# app.root_path is the directory where app.py is located (e.g., /app)
DISHES_DIRECTORY = os.path.abspath(os.path.join(app.root_path, 'dishes'))

# Load recipe data once when the app starts
recipes_data = []
try:
    with open('recipes.json', 'r', encoding='utf-8') as f:
        recipes_data = json.load(f)
except FileNotFoundError:
    print("ERROR: recipes.json not found. Make sure to run parser.py first.")
    # You might want to exit or provide default empty data if the file is critical
except json.JSONDecodeError:
    print("ERROR: recipes.json is not valid JSON.")

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', recipes=recipes_data)

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    try:
        recipe = recipes_data[recipe_id]
        
        # Image paths for the template need to be relative to the 'dishes' directory.
        # The original image_paths from parser are relative to the .md file.
        # source_file from parser is like: "dishes/category/recipe_folder/recipe.md"
        # image_path from parser is like: "image.jpg"
        # We need to construct: "category/recipe_folder/image.jpg"
        
        template_image_paths = []
        if recipe.get('image_paths'):
            # recipe['source_file'] is like "dishes/cat1/recipe1/recipe.md" (from parser)
            # os.path.dirname gives "dishes/cat1/recipe1"
            recipe_md_dir_in_repo = os.path.dirname(recipe.get('source_file', ''))
            
            path_obj = Path(recipe_md_dir_in_repo)
            if path_obj.parts and path_obj.parts[0].lower() == 'dishes':
                # base_path_for_image will be "cat1/recipe1"
                base_path_for_image = Path(*path_obj.parts[1:])
            else:
                # Fallback if source_file is not directly under 'dishes' (e.g. "cat1/recipe1")
                # This might occur if source_file was "cat1/recipe1/recipe.md" without "dishes/" prefix
                base_path_for_image = path_obj

            for img_path_in_md in recipe['image_paths']: # img_path_in_md is like "image1.jpg" or "subdir/image.png"
                # final_image_path should be "cat1/recipe1/image1.jpg"
                final_image_path = base_path_for_image / img_path_in_md
                # Use as_posix() for URL consistency (forward slashes)
                template_image_paths.append(final_image_path.as_posix())

        recipe_for_template = recipe.copy()
        recipe_for_template['image_paths'] = template_image_paths

        return render_template('recipe.html', recipe=recipe_for_template)
    except IndexError:
        abort(404)
    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error processing recipe ID {recipe_id}: {e}")
        abort(500) # Internal server error

@app.route('/images/<path:filename>')
def serve_image(filename):
    # Serve files from the DISHES_DIRECTORY
    # filename is expected to be a path relative to DISHES_DIRECTORY
    # e.g. category/recipe_folder/image.jpg
    return send_from_directory(DISHES_DIRECTORY, filename)

if __name__ == '__main__':
    # For local development, ensure FLASK_ENV=development for debug mode.
    # The app.run(debug=True) is also an option but FLASK_ENV is preferred.
    app.run(debug=True)
