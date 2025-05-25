import unittest
import os
import json
import shutil
import tempfile
from pathlib import Path
from app import app # Import the Flask app instance from your app.py

class TestApp(unittest.TestCase):

    def setUp(self):
        # Configure the app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for form tests if any (not in this app)
        self.client = app.test_client()

        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create a dummy recipes.json
        self.recipes_file_path = Path(self.test_dir) / "recipes.json"
        self.dummy_recipes = [
            {
                "title": "Test Recipe 1",
                "description": "Desc 1",
                "difficulty": "Easy",
                "ingredients": ["Ing1", "Ing2"],
                "calculations": {"Time": "30 mins"},
                "instructions": ["Step1", "Step2"],
                "image_paths": ["image1.jpg"], # Path relative to the MD file itself
                "category": "cat1",
                "source_file": "dishes/cat1/recipe1/recipe1.md"
            },
            {
                "title": "Test Recipe 2",
                "description": "Desc 2",
                "difficulty": "Medium",
                "ingredients": ["Ing3", "Ing4"],
                "calculations": {},
                "instructions": ["Step3", "Step4"],
                "image_paths": [],
                "category": "cat2",
                "source_file": "dishes/cat2/recipe2/recipe2.md"
            }
        ]
        with open(self.recipes_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.dummy_recipes, f)
        
        # Store original recipes_data and patch it for tests
        import app as current_app_module
        self.original_recipes_data = current_app_module.recipes_data
        current_app_module.recipes_data = self.dummy_recipes

        self.mock_dishes_dir = Path(self.test_dir) / "dishes"
        self.mock_dishes_dir.mkdir(parents=True, exist_ok=True)
        
        self.image_cat_dir = self.mock_dishes_dir / "cat1" / "recipe1"
        self.image_cat_dir.mkdir(parents=True, exist_ok=True)
        self.dummy_image_path = self.image_cat_dir / "image1.jpg"
        with open(self.dummy_image_path, 'wb') as img_f: # write in binary mode for images
            img_f.write(b"dummy jpeg data") 

        # Patch DISHES_DIRECTORY in the app module (app.py)
        import app as current_app_module
        self.original_dishes_directory = current_app_module.DISHES_DIRECTORY
        current_app_module.DISHES_DIRECTORY = str(self.mock_dishes_dir)


    def tearDown(self):
        shutil.rmtree(self.test_dir)
        # Restore original DISHES_DIRECTORY and recipes_data in the app module
        import app as current_app_module
        current_app_module.DISHES_DIRECTORY = self.original_dishes_directory
        current_app_module.recipes_data = self.original_recipes_data


    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"All Recipes", response.data)
        self.assertIn(b"Test Recipe 1", response.data)
        self.assertIn(b"Test Recipe 2", response.data)

    def test_recipe_detail_route_valid(self):
        response = self.client.get('/recipe/0') # First recipe
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Recipe 1", response.data)
        self.assertIn(b"Ing1", response.data)
        self.assertIn(b'src="/images/cat1/recipe1/image1.jpg"', response.data)

    def test_recipe_detail_route_invalid(self):
        response = self.client.get('/recipe/99') # Out of bounds
        self.assertEqual(response.status_code, 404)

    def test_serve_image_route_valid(self):
        image_path_for_route = "cat1/recipe1/image1.jpg"
        response = self.client.get(f'/images/{image_path_for_route}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"dummy jpeg data")
        # Werkzeug's test client / send_from_directory might not set content_type perfectly for dummy files
        # without a proper mimetype guess based on filename, so this check is broad.
        self.assertTrue(response.content_type.startswith('image/'))


    def test_serve_image_route_invalid(self):
        response = self.client.get('/images/nonexistent/image.jpg')
        self.assertEqual(response.status_code, 404)
    
    def test_recipe_detail_route_no_images(self):
        response = self.client.get('/recipe/1') # Second recipe, no images
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Recipe 2", response.data)
        self.assertNotIn(b"<img src", response.data)

if __name__ == '__main__':
    unittest.main()
