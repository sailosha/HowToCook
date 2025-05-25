import os
import markdown
from flask import Flask, render_template, url_for

app = Flask(__name__)

def load_recipes():
    recipes = []
    base_recipes_dir = os.path.join(os.path.dirname(__file__), 'dishes')
    if not os.path.exists(base_recipes_dir):
        return recipes # Return empty list if 'dishes' directory doesn't exist
    for root, _, files in os.walk(base_recipes_dir):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                # Calculate path relative to base_recipes_dir
                relative_path = os.path.relpath(filepath, base_recipes_dir)
                recipe_title = os.path.splitext(os.path.basename(file))[0].replace('-', ' ').title()
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    html_content = markdown.markdown(content)
                    recipes.append({'title': recipe_title, 'html_content': html_content, 'path': relative_path})
                except Exception as e:
                    print(f"Error processing file {filepath}: {e}") # Log error
    return recipes

@app.route('/')
def homepage():
    recipes = load_recipes()
    return render_template('index.html', recipes=recipes)

@app.route('/recipe/<path:path>')
def recipe_page(path):
    recipes = load_recipes()
    recipe = next((r for r in recipes if r['path'] == path), None)
    if recipe:
        return render_template('recipe.html', recipe=recipe)
    else:
        return ("Recipe not found", 404)

if __name__ == '__main__':
    app.run(debug=True)
