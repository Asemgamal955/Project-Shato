import json
import os

def split_data_by_category(input_file="converted_shato_data.json", output_dir="split_data"):
    """
    Split the converted SHATO training data by category into separate files.
    """
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the converted data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Group data by category
    categories = {}
    for entry in data:
        category = entry["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(entry)
    
    # Save each category to a separate file
    for category, entries in categories.items():
        output_file = os.path.join(output_dir, f"{category}_examples.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(entries)} {category} examples to {output_file}")
    
    return categories

def merge_category_files(category, new_file, existing_file=None):
    """
    Merge new category data with existing category data.
    
    Args:
        category: The category name (e.g., 'rotate', 'move_to')
        new_file: Path to the new category file
        existing_file: Path to existing category file (optional)
    """
    
    # Load new data
    with open(new_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)
    
    # Load existing data if provided
    existing_data = []
    if existing_file and os.path.exists(existing_file):
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        print(f"Loaded {len(existing_data)} existing {category} examples")
    
    # Combine data
    all_data = existing_data + new_data
    
    # Remove duplicates based on user_input
    seen_inputs = set()
    unique_data = []
    duplicates = 0
    
    for entry in all_data:
        user_input = entry["user_input"].strip().lower()
        if user_input not in seen_inputs:
            seen_inputs.add(user_input)
            unique_data.append(entry)
        else:
            duplicates += 1
    
    # Save merged data
    output_file = f"enhanced_{category}_examples.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, indent=2, ensure_ascii=False)
    
    print(f"Enhanced {category} data:")
    print(f"  New examples: {len(new_data)}")
    print(f"  Existing examples: {len(existing_data)}")
    print(f"  Total unique examples: {len(unique_data)}")
    print(f"  Duplicates removed: {duplicates}")
    print(f"  Saved to: {output_file}")
    
    return unique_data

def show_command_variety_analysis(data_file):
    """
    Analyze and display the variety of command phrasings to show improved coverage.
    """
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Group by actual command used
    commands = {}
    for entry in data:
        expected_output = entry["expected_output"]
        command = expected_output.get("command")
        user_input = entry["user_input"]
        
        if command not in commands:
            commands[command] = set()
        
        # Extract key phrases that indicate the command
        if command == "move_to":
            # Look for movement keywords
            movement_words = ["move", "go", "navigate", "travel", "proceed", "head", "coordinates"]
            for word in movement_words:
                if word in user_input.lower():
                    commands[command].add(word)
        elif command == "rotate":
            # Look for rotation keywords  
            rotation_words = ["rotate", "turn", "spin", "clockwise", "counter-clockwise", "degrees"]
            for word in rotation_words:
                if word in user_input.lower():
                    commands[command].add(word)
        elif command == "start_patrol":
            # Look for patrol keywords
            patrol_words = ["patrol", "guard", "monitor", "watch", "begin", "start"]
            for word in patrol_words:
                if word in user_input.lower():
                    commands[command].add(word)
    
    print(f"\nCommand keyword variety analysis for {data_file}:")
    for command, keywords in commands.items():
        if keywords:  # Only show commands with keywords found
            print(f"{command}: {sorted(keywords)}")

# Example usage
if __name__ == "__main__":
    print("=== Splitting converted SHATO data by category ===")
    categories = split_data_by_category()
    
    print(f"\n=== Created files for {len(categories)} categories ===")
    
    # Example of enhancing existing category files
    # You would run this for each category you have existing data for
    
    existing_category_files = {
        "rotate": "rotate.json",
        "move_to": "move_to.json", 
        "start_patrol": "patrol.json",
        "chat": "chat_examples.json"
    }
    
    print(f"\n=== Enhancing existing category files ===")
    for category in categories.keys():
        new_file = f"split_data/{category}_examples.json"
        existing_file = existing_category_files.get(category)
        
        if existing_file:
            print(f"\nEnhancing {category} category:")
            enhanced_data = merge_category_files(category, new_file, existing_file)
            show_command_variety_analysis(f"enhanced_{category}_examples.json")
        else:
            print(f"\nNo existing file for {category}, using new data only")
            show_command_variety_analysis(new_file)