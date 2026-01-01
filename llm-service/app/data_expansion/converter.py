import json

def convert_shato_training_data(input_file="shato_training_data.json", output_file="converted_shato_data.json"):
    """
    Convert the SHATO training data from 'input' key format to 'user_input' key format
    to match the existing split training data structure.
    """
    
    # Read the original data
    with open(input_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # Convert each entry
    converted_data = []
    for entry in original_data:
        converted_entry = {
            "user_input": entry["input"],  # Change "input" to "user_input"
            "expected_output": entry["expected_output"],
            "category": entry["category"],
            "type": entry["type"]
        }
        converted_data.append(converted_entry)
    
    # Save the converted data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, indent=2, ensure_ascii=False)
    
    print(f"Converted {len(converted_data)} entries")
    print(f"Saved to {output_file}")
    
    # Print some statistics
    categories = {}
    for entry in converted_data:
        cat = entry["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nCategory distribution:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} examples")
    
    return converted_data

def merge_with_existing_data(converted_data, existing_files):
    """
    Merge the converted SHATO data with existing split training data files.
    
    Args:
        converted_data: The converted SHATO training data
        existing_files: List of paths to existing training data files
    """
    
    # Load existing data
    existing_data = []
    for file_path in existing_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_data.extend(data)
                print(f"Loaded {len(data)} entries from {file_path}")
        except FileNotFoundError:
            print(f"Warning: {file_path} not found, skipping...")
    
    # Combine all data
    all_data = existing_data + converted_data
    
    # Remove duplicates based on user_input (optional)
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
    
    print(f"\nMerged data statistics:")
    print(f"Total entries: {len(all_data)}")
    print(f"Unique entries: {len(unique_data)}")
    print(f"Duplicates removed: {duplicates}")
    
    # Save merged data
    with open("merged_training_data.json", 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, indent=2, ensure_ascii=False)
    
    print("Saved merged data to merged_training_data.json")
    
    return unique_data

def analyze_command_variations(data):
    """
    Analyze the variety of phrasings for each command to help understand coverage.
    """
    command_variations = {}
    
    for entry in data:
        category = entry["category"]
        user_input = entry["user_input"]
        
        if category not in command_variations:
            command_variations[category] = []
        
        command_variations[category].append(user_input)
    
    print("\nCommand variation analysis:")
    for category, variations in command_variations.items():
        print(f"\n{category.upper()} ({len(variations)} variations):")
        # Show first 5 variations as examples
        for i, variation in enumerate(variations[:5]):
            print(f"  {i+1}. {variation}")
        if len(variations) > 5:
            print(f"  ... and {len(variations) - 5} more variations")

# Example usage
if __name__ == "__main__":
    # Convert the SHATO data
    converted_data = convert_shato_training_data()
    
    # Example of merging with existing split data files
    # Replace these with your actual file paths
    existing_files = [
        "rotate_examples.json",
        "move_to_examples.json", 
        "start_patrol_examples.json",
        "chat_examples.json"
    ]
    
    # Uncomment to merge with existing data
    # merged_data = merge_with_existing_data(converted_data, existing_files)
    
    # Analyze command variations
    analyze_command_variations(converted_data)