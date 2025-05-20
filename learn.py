import argparse
import os
import sys

# --- Path Setup ---
# Get the directory of the current script (learn.py)
current_script_path = os.path.abspath(__file__)
# new_agent_dir is the directory containing learn.py (e.g., NewAgent)
new_agent_dir = os.path.dirname(current_script_path)
# scripts_dir is NewAgent/scripts
scripts_dir = os.path.join(new_agent_dir, 'scripts')

# Add directories to sys.path if not already there,
# prioritizing new_agent_dir for top-level package resolution if needed.
if new_agent_dir not in sys.path:
    sys.path.insert(0, new_agent_dir) # For imports like `from scripts import ...`
if scripts_dir not in sys.path:
    # This might be redundant if new_agent_dir allows `from scripts ...`
    # but can be useful if scripts import other scripts directly by name.
    sys.path.insert(0, scripts_dir)

# Now imports from 'scripts' should work
try:
    from scripts import self_explorer
    from scripts.utils import print_with_color
except ImportError as e:
    print(f"Error importing agent modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Please ensure '{new_agent_dir}' and '{scripts_dir}' are correctly structured or in your PYTHONPATH.")
    sys.exit(1)

def main_learn():
    parser = argparse.ArgumentParser(
        description="AppAgent - Launcher for task-driven or exploration mode."
    )
    parser.add_argument(
        "--package",
        type=str,
        required=True,
        help="The package name of the target application (e.g., com.example.app)."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="The task description (e.g., 'Search for cats and play a video') or a general app description for exploration (e.g., 'This is a calculator app. Explore its features.')."
    )
    parser.add_argument(
        "--root_dir",
        type=str,
        default=".", # Default to the directory where learn.py is run from
        help="The root directory for storing app-specific outputs and logs. Defaults to the current directory."
    )
    args = parser.parse_args()

    print_with_color("AppAgent: Launching via learn.py", "blue")

    # --- Prepare arguments for self_explorer.main ---
    package_name = args.package
    user_input = args.input
    # Use abspath for root_dir to ensure it's always a full path
    root_dir_abs = os.path.abspath(args.root_dir)

    try:
        print_with_color(
            f"Calling self_explorer.main() with:\n"
            f"  Package Name: {package_name}\n"
            f"  User Input: {user_input}\n"
            f"  Root Directory: {root_dir_abs}",
            "yellow"
        )
        # Call self_explorer.main directly with keyword arguments
        # self_explorer.main now expects these arguments.
        # The root_dir in self_explorer.py's argparse setup will be overridden by root_dir_abs here.
        self_explorer.main(
            package_name_arg=package_name,
            user_input_arg=user_input,
            root_dir_arg=root_dir_abs,
        )
    except Exception as e:
        print_with_color(f"An error occurred during agent execution: {e}", "red")
        import traceback
        traceback.print_exc()
    finally:
        print_with_color("Agent process (called from learn.py) has finished or encountered an error.", "blue")

if __name__ == "__main__":
    main_learn()