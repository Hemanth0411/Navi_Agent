import os
import shutil
from pathlib import Path

def cleanup_exploration_data(app_name: str, root_dir: str = ".") -> None:
    """
    Clean up exploration data (screenshots, XMLs, logs) after agent completes exploration.
    Only keeps the auto_docs directory which is needed for future runs.
    
    Args:
        app_name (str): Name of the app that was explored
        root_dir (str): Root directory of the project (default: current directory)
    """
    # Validate app_name
    if not app_name:
        print("Warning: No app name provided for cleanup")
        return
        
    # Construct paths
    apps_dir = os.path.join(root_dir, "apps")
    app_dir = os.path.join(apps_dir, app_name)
    demos_dir = os.path.join(app_dir, "demos")
    
    # Check if directories exist
    if not os.path.exists(demos_dir):
        print(f"No demos directory found for {app_name}")
        return
    
    # Get all exploration directories
    exploration_dirs = [d for d in os.listdir(demos_dir) 
                       if os.path.isdir(os.path.join(demos_dir, d)) 
                       and d.startswith("self_explore_")]
    
    for explore_dir in exploration_dirs:
        explore_path = os.path.join(demos_dir, explore_dir)
        
        # Clean up screenshots
        screenshots_dir = os.path.join(explore_path, "screenshots")
        if os.path.exists(screenshots_dir):
            try:
                shutil.rmtree(screenshots_dir)
                print(f"Cleaned up screenshots in {explore_dir}")
            except Exception as e:
                print(f"Error cleaning screenshots: {e}")
        
        # Clean up XMLs
        xmls_dir = os.path.join(explore_path, "xmls")
        if os.path.exists(xmls_dir):
            try:
                shutil.rmtree(xmls_dir)
                print(f"Cleaned up XMLs in {explore_dir}")
            except Exception as e:
                print(f"Error cleaning XMLs: {e}")
        
        # Clean up logs
        logs_dir = os.path.join(explore_path, "logs")
        if os.path.exists(logs_dir):
            try:
                shutil.rmtree(logs_dir)
                print(f"Cleaned up logs in {explore_dir}")
            except Exception as e:
                print(f"Error cleaning logs: {e}")
        
        # Remove empty exploration directory
        try:
            if not os.listdir(explore_path):  # Check if directory is empty
                os.rmdir(explore_path)
                print(f"Removed empty exploration directory {explore_dir}")
        except Exception as e:
            print(f"Error removing exploration directory: {e}")

def verify_cleanup(app_name: str, root_dir: str = ".") -> bool:
    """
    Verify that cleanup was successful by checking if only auto_docs remains.
    
    Args:
        app_name (str): Name of the app to verify
        root_dir (str): Root directory of the project
        
    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    apps_dir = os.path.join(root_dir, "apps")
    app_dir = os.path.join(apps_dir, app_name)
    
    # Check if auto_docs exists
    auto_docs_dir = os.path.join(app_dir, "auto_docs")
    if not os.path.exists(auto_docs_dir):
        print(f"Warning: auto_docs directory not found for {app_name}")
        return False
    
    # Check if demos directory is empty or doesn't exist
    demos_dir = os.path.join(app_dir, "demos")
    if os.path.exists(demos_dir):
        if os.listdir(demos_dir):  # If directory is not empty
            print(f"Warning: demos directory still contains data for {app_name}")
            return False
    
    print(f"Cleanup verified for {app_name}")
    return True

# Example usage in learn.py:
"""
# Add this at the end of your exploration process
from cleanup import cleanup_exploration_data, verify_cleanup

# After exploration is complete
cleanup_exploration_data(app_name)
if verify_cleanup(app_name):
    print("Cleanup successful")
else:
    print("Cleanup verification failed")
"""
