import unittest
import os
import json
import shutil
import tempfile
from pathlib import Path
from parser import parse_recipes # Assuming parser.py is in the same directory or accessible via PYTHONPATH

class TestParser(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory to simulate the 'dishes' structure
        self.test_dir = tempfile.mkdtemp()
        # This will be our 'base_dir_override' for parse_recipes
        self.mock_dishes_path = Path(self.test_dir)

    def tearDown(self):
        # Remove the temporary directory after the test
        shutil.rmtree(self.test_dir)

    def _create_md_file(self, category, filename, content, images=None):
        """Helper to create markdown files and associated image files."""
        cat_path = self.mock_dishes_path / category
        cat_path.mkdir(parents=True, exist_ok=True)
        
        md_file_path = cat_path / filename
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if images:
            for img_name in images:
                img_path = cat_path / img_name
                # Create a dummy image file
                with open(img_path, 'w') as img_f:
                    img_f.write("dummy image data") # Content doesn't matter for parser test
        return md_file_path

    def test_well_formed_recipe(self):
        content = """# Test Recipe 1
Description for recipe 1.

## 预估烹饪难度
简单

## 必备原料和工具
- Ingredient A
- Tool B

## 计算
- 糖: 10克
- 盐: 5克

## 操作
1. Step 1
2. Step 2

![Image Alt Text 1](image1.jpg)
Some text
![Image Alt Text 2](subdir/image2.png)
"""
        self._create_md_file("test_cat1", "recipe1.md", content, images=["image1.jpg"])
        # Manually create subdir for the second image and the image itself
        (self.mock_dishes_path / "test_cat1" / "subdir").mkdir(exist_ok=True)
        with open(self.mock_dishes_path / "test_cat1" / "subdir" / "image2.png", 'w') as img_f:
            img_f.write("dummy image data")

        recipes = parse_recipes(base_dir_override=str(self.mock_dishes_path))
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]

        self.assertEqual(recipe['title'], "Test Recipe 1")
        self.assertEqual(recipe['description'], "Description for recipe 1.")
        self.assertEqual(recipe['difficulty'], "简单")
        self.assertListEqual(recipe['ingredients'], ["Ingredient A", "Tool B"])
        self.assertDictEqual(recipe['calculations'], {"糖": "10克", "盐": "5克"})
        self.assertListEqual(recipe['instructions'], ["Step 1", "Step 2"]) # parse_markdown_list strips markers
        self.assertListEqual(sorted(recipe['image_paths']), sorted(["image1.jpg", "subdir/image2.png"]))
        self.assertEqual(recipe['category'], "test_cat1")
        # Check source_file path construction
        expected_source_file = os.path.join("dishes", "test_cat1", "recipe1.md")
        self.assertEqual(Path(recipe['source_file']), Path(expected_source_file))


    def test_missing_optional_sections(self):
        content = """# Test Recipe 2
Only description here.

## 必备原料和工具
- Ingredient X

## 操作
1. Do something
"""
        self._create_md_file("test_cat2", "recipe2.md", content)
        recipes = parse_recipes(base_dir_override=str(self.mock_dishes_path))
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]

        self.assertEqual(recipe['title'], "Test Recipe 2")
        self.assertEqual(recipe['description'], "Only description here.")
        self.assertIsNone(recipe['difficulty']) 
        self.assertListEqual(recipe['ingredients'], ["Ingredient X"])
        self.assertDictEqual(recipe['calculations'], {}) # Expect {} as per parse_key_value_pairs(None)
        self.assertListEqual(recipe['instructions'], ["Do something"]) # parse_markdown_list strips markers
        self.assertListEqual(recipe['image_paths'], [])
        self.assertEqual(recipe['category'], "test_cat2")

    def test_no_images(self):
        content = """# Test Recipe 3
No images in this one.
"""
        self._create_md_file("test_cat3", "recipe3.md", content)
        recipes = parse_recipes(base_dir_override=str(self.mock_dishes_path))
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]
        self.assertListEqual(recipe['image_paths'], [])

    def test_category_extraction_general(self):
        # Test for recipe directly under the base_dir (e.g. dishes/some_recipe.md)
        content = "# General Recipe"
        # Create file directly in self.mock_dishes_path
        with open(self.mock_dishes_path / "general_recipe.md", 'w', encoding='utf-8') as f:
            f.write(content)
        
        recipes = parse_recipes(base_dir_override=str(self.mock_dishes_path))
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]
        self.assertEqual(recipe['category'], "general")
        expected_source_file = os.path.join("dishes", "general_recipe.md")
        self.assertEqual(Path(recipe['source_file']), Path(expected_source_file))

    def test_empty_file(self):
        self._create_md_file("empty_cat", "empty.md", "")
        recipes = parse_recipes(base_dir_override=str(self.mock_dishes_path))
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]
        self.assertEqual(recipe['title'], "Untitled Recipe")
        self.assertEqual(recipe['description'], "")
        self.assertIsNone(recipe['difficulty'])
        self.assertListEqual(recipe['ingredients'], [])
        self.assertDictEqual(recipe['calculations'], {}) # parse_key_value_pairs(None) returns {}
        self.assertListEqual(recipe['instructions'], [])
        self.assertListEqual(recipe['image_paths'], [])
        self.assertEqual(recipe['category'], "empty_cat")

    def test_recipe_in_deeper_subdirectory(self):
        # e.g., dishes/main_cat/sub_cat/recipe.md -> category should be 'main_cat'
        deep_cat_path = self.mock_dishes_path / "main_cat" / "sub_cat"
        deep_cat_path.mkdir(parents=True, exist_ok=True)
        
        content = "# Deep Recipe"
        with open(deep_cat_path / "deep_recipe.md", 'w', encoding='utf-8') as f:
            f.write(content)

        recipes = parse_recipes(base_dir_override=str(self.mock_dishes_path))
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]
        self.assertEqual(recipe['category'], "main_cat") 
        expected_source_file = os.path.join("dishes", "main_cat", "sub_cat", "deep_recipe.md")
        self.assertEqual(Path(recipe['source_file']), Path(expected_source_file))


if __name__ == '__main__':
    unittest.main()
