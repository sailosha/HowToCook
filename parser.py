import os
import glob
import json
import re
from markdown import Markdown # Using python-markdown's core
from pathlib import Path

def extract_section_content(content, section_title):
    """
    Extracts content from a specific section in Markdown text.
    A section is defined by a H2 heading (## Section Title).
    Content is everything between this heading and the next heading (any level) or end of doc.
    """
    # Regex to find the section and capture its content until the next heading or EOF
    # It looks for '## section_title', then a newline, then captures (non-greedy)
    # until it hits another heading '^\s*#+' or the end of the string '$' (changed from \Z for section end)
def extract_section_content(content, section_title):
    lines = content.splitlines()
    in_section = False
    section_lines = []
    
    normalized_param_title = section_title.lower().strip()

    for line in lines:
        stripped_line = line.strip()
        normalized_line_lower = stripped_line.lower()

        if in_section:
            # Stop if we hit another H2 or H3 heading
            if stripped_line.startswith('##') or stripped_line.startswith('###'):
                break 
            section_lines.append(line) # Keep original line content
        else:
            if normalized_line_lower.startswith("##"):
                # Extract text after "##" and normalize (strip, lower)
                title_part_on_line = stripped_line[2:].strip().lower()
                if title_part_on_line == normalized_param_title:
                    in_section = True
                    # Content is on subsequent lines, so don't add this heading line
    
    if section_lines:
        return "\n".join(section_lines).strip() # Strip overall block
    return None

def parse_markdown_list(text):
    """Parses a Markdown list (lines starting with -, *, or number.) into a list of strings."""
    if not text:
        return []
    # Regex to find list items starting with 'DIGIT.', '*', or '-'
    # It captures the content after the marker and leading spaces.
    return [item.strip() for item in re.findall(r'^(?:[*-]|\d+\.)\s+(.+)', text, re.MULTILINE)]

def parse_key_value_pairs(text):
    """Parses lines like 'Key: Value' or 'Key（Value）' into a dictionary."""
    if not text:
        return {}
    data = {}
    # Handles "Key: Value", "Key：Value", "Key Value" (less specific), "Key（注释）Value"
    # Also handles optional list markers like "- Key: Value"
    # Prioritizing more specific patterns first
    patterns = [
        # Key: Value or Key： Value, optionally starting with a list marker
        r'^\s*(?:[*-]\s+)?([^\n:]+?)\s*[:：]\s*(.+?)\s*$',
        # Key（Comment）Value, optionally starting with a list marker
        r'^\s*(?:[*-]\s+)?([^\n（]+?)\s*（(.+?)）\s*(.+?)\s*$',
        # Key Value (more general), optionally starting with a list marker
        r'^\s*(?:[*-]\s+)?([^\s]+)\s+([^\s]+.*)\s*$'
    ]
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        matched = False
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 3: # Key（Comment）Value
                    key, comment, value = match.groups()
                    data[key.strip()] = f"{value.strip()} ({comment.strip()})"
                elif len(match.groups()) == 2:
                    key, value = match.groups()
                    data[key.strip()] = value.strip()
                matched = True
                break
        if not matched and line: # Fallback for lines that might be just values or unparsed
            # This could be a simple list item without a clear key, decide how to handle
            # For now, skip if no clear key-value structure
            pass
    return data


def parse_recipes(base_dir_override=None):
    recipes_data = []
    # Using Path for easier path manipulation
    if base_dir_override:
        base_dir = Path(base_dir_override)
    else:
        base_dir = Path('dishes')
    
    markdown_files = glob.glob(str(base_dir / '**/*.md'), recursive=True)

    for filepath in markdown_files:
        path_obj = Path(filepath)
        try:
            category_parts = path_obj.parent.parts
            # Determine category based on the path relative to the base_dir
            # path_obj.parent is the directory containing the .md file
            # We want the first directory *after* base_dir
            relative_path_to_parent = path_obj.parent.relative_to(base_dir)
            if relative_path_to_parent.parts:
                category = relative_path_to_parent.parts[0]
            else:
                # If the file is directly in base_dir (e.g. temp_dishes/recipe.md)
                category = "general"


            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Title (first H1)
            title_match = re.search(r'^#\s+(.+?)\s*$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else "Untitled Recipe"

            # Description (text immediately following title until the next heading)
            description = ""
            if title_match:
                search_start_pos = title_match.end()
                # Find the start of the next heading (##, ###, etc.) or end of content
                next_heading_match = re.search(r'^\s*##+', content[search_start_pos:], re.MULTILINE)
                
                description_end_pos = len(content) # Default to end of content
                if next_heading_match:
                    description_end_pos = search_start_pos + next_heading_match.start()
                
                description_text = content[search_start_pos:description_end_pos].strip()
                # Join lines that are part of the same paragraph, then strip leading/trailing whitespace.
                # This handles multi-line descriptions better.
                description_lines = [line.strip() for line in description_text.splitlines()]
                description = "\n".join(filter(None, description_lines)) # Remove empty lines from list then join
            
            # Using the helper to extract sections
            difficulty_text = extract_section_content(content, "预估烹饪难度")
            
            ingredients_text = extract_section_content(content, "必备原料和工具")
            ingredients_list = []
            if ingredients_text:
                raw_ingredients = parse_markdown_list(ingredients_text)
                if not raw_ingredients and ingredients_text: 
                     ingredients_list = [line.strip() for line in ingredients_text.split('\n') if line.strip()]
                else:
                    ingredients_list = raw_ingredients

            calculations_text = extract_section_content(content, "计算")
            calculations_data = parse_key_value_pairs(calculations_text)
            if not calculations_data and calculations_text: 
                calculations_data = calculations_text

            instructions_text = extract_section_content(content, "操作")
            instructions_list = parse_markdown_list(instructions_text)
            if not instructions_list and instructions_text: 
                instructions_list = [line.strip() for line in instructions_text.split('\n') if line.strip()]

            image_paths = []
            for img_match in re.finditer(r'!\[.*?\]\((?!https?://)(.*?)\)', content):
                img_path = img_match.group(1)
                image_paths.append(img_path)
            
            recipe_dict = {
                "title": title,
                "description": description,
                "difficulty": difficulty_text,
                "ingredients": ingredients_list,
                "calculations": calculations_data,
                "instructions": instructions_list,
                "image_paths": image_paths,
                "category": category,
            }
            # Store source_file path relative to the original base_dir name ('dishes') for consistency
            # This makes sure that when app.py uses these paths, it still works as if from 'dishes'
            original_base_name = "dishes" # Default name of the main recipes directory
            path_relative_to_current_basedir = path_obj.relative_to(base_dir)
            recipe_dict["source_file"] = str(Path(original_base_name) / path_relative_to_current_basedir)
            
            recipes_data.append(recipe_dict)

        except Exception as e:
            print(f"Error parsing file {filepath}: {e}")
            recipes_data.append({
                "title": "Error parsing file",
                "source_file": filepath,
                "error": str(e),
                "category": "error",
                "description": None, "difficulty": None, "ingredients": [], 
                "calculations": None, "instructions": [], "image_paths": []
            })

    return recipes_data

if __name__ == "__main__":
    all_recipes = parse_recipes()
    output_path = Path("recipes.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_recipes, f, ensure_ascii=False, indent=4)
    print(f"Successfully parsed {len(all_recipes)} recipes into {output_path}")
