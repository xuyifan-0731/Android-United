from definition import *
from utils_mobile.xml_tool import UIXMLTree

def find_matching_subtrees(tree, search_str):
    """
    Finds all subtrees in a given JSON-like dictionary tree where any key or
    leaf node value contains the given string. Returns a list of all matching subtrees,
    ensuring that no higher-level nodes are included unless they themselves match.

    Parameters:
    - tree (dict): The tree to search within.
    - search_str (str): The substring to search for in keys and leaf node values.

    Returns:
    - list: A list of dictionaries, each representing a matching subtree.
    """

    # Helper function to recursively search through the tree
    def search_tree(current_tree):
        # Initialize a local variable to store potential matches within this subtree
        local_matches = []

        # Iterate through each key and value pair in the current tree
        for key, value in current_tree.items():
            # Check if the key itself contains the search string
            if search_str in key:
                # Directly append this subtree since the key matches
                local_matches.append({key: value})
            elif isinstance(value, dict):
                # If the value is a dictionary, recurse into it
                result = search_tree(value)
                if result:
                    # Only append if the recursion found a match
                    local_matches.extend(result)
            elif isinstance(value, str) and search_str in value:
                # If the value is a string and contains the search string, append this leaf
                local_matches.append({key: value})

        # Return any matches found in this part of the tree
        return local_matches

    # Start the search from the root of the tree
    matched_subtrees = search_tree(tree)

    return matched_subtrees


def find_subtrees_of_parents_with_key(tree, search_key):
    """
    Finds the entire subtrees for all parent nodes of any nodes containing the given key in a JSON-like dictionary tree.
    Each subtree is collected in a list.

    Parameters:
    - tree (dict): The tree to search within.
    - search_key (str): The key to search for in the tree.

    Returns:
    - list: A list of dictionaries, each representing the subtree of a parent that has a child node with the search_key.
    """
    parent_subtrees = []  # To store the subtrees of parents that contain the search_key

    # Helper function to recursively search through the tree
    def search_tree(current_tree, parent=None):
        # Iterate through each key and value pair in the current tree
        for key, value in current_tree.items():
            if search_key in key:
                if parent:
                    parent_subtrees.append({parent: current_tree})  # Capture the parent's subtree
                return True  # Found the key, mark this path as containing the key
            elif isinstance(value, dict):
                # If the value is a dictionary, recurse into it
                search_tree(value, key)  # Continue to search deeper

    # Start the recursive search from the root
    search_tree(tree)

    return parent_subtrees



def get_compressed_xml(xml_path):
    xml_parser = UIXMLTree()
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_str = f.read()
    try:
        compressed_xml = xml_parser.process(xml_str, level=1, str_type="json").strip()
    except Exception as e:
        compressed_xml = None
        print(f"XML compressed failure: {e}")
    return compressed_xml

def get_xml_list(xml_path):
    xml_parser = UIXMLTree()
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_str = f.read()
    try:
        compressed_xml = xml_parser.process(xml_str, level=1, str_type="list")
    except Exception as e:
        compressed_xml = None
        print(f"XML compressed failure: {e}")
    return compressed_xml

def dump_xml(controller, device_name = None, accessiblity = False, task_id = "0"):
    save_dir = "logs/auto-test/xmls"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    if accessiblity:
        controller.get_ac_xml(prefix=task_id, save_dir=save_dir)
    else:
        controller.get_xml(prefix=task_id, save_dir=save_dir)
    xml_path = os.path.join(save_dir, f"{task_id}.xml")
    xml_compressed = get_compressed_xml(xml_path)
    print(xml_compressed)
    return json.loads(xml_compressed)

def get_current_compressed_xml():
    controller, device_name = get_mobile_device_and_name()
    output_json = dump_xml(controller, device_name, False, "0")
    return output_json

def extract_bounds(node, path=""):
    result = []
    for key, value in node.items():
        current_path = f"{path}{key} "
        if isinstance(value, dict):
            result.extend(extract_bounds(value, current_path))
        elif key == "bounds":
            result.append({"key": path.strip(), "value": value})
    return result