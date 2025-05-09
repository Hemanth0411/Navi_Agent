import argparse
import os
import sys

# Ensure the 'scripts' directory and the NewAgent directory are in Python path
current_script_path = os.path.abspath(__file__)
new_agent_dir = os.path.dirname(current_script_path)
scripts_dir = os.path.join(new_agent_dir, 'scripts')

if new_agent_dir not in sys.path:
    sys.path.insert(0, new_agent_dir)
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# Now we can import from scripts as a package
from scripts import self_explorer
from scripts.utils import print_with_color

def main_learn(): # Renamed to avoid conflict if self_explorer also has main
    parser = argparse.ArgumentParser(description="AppAgent - Autonomous Exploration")
    parser.add_argument("--app", type=str, help="The name of the target application to explore.")
    parser.add_argument("--root_dir", type=str, default=".", help="The root directory for the agent's operation (should be NewAgent).")
    args = parser.parse_args()

    # Pass the arguments to self_explorer.main
    # self_explorer.main expects args to be a dictionary or an object with app and root_dir attributes
    # We can simulate the sys.argv that self_explorer.main would expect if run directly
    # or modify self_explorer.main to accept these as direct parameters.
    # For now, let's adjust learn.py to prepare for calling self_explorer.main().
    # The self_explorer.py already uses argparse, so we can just call its main.

    print_with_color("AppAgent: Autonomous Exploration Mode via learn.py", "blue")

    # Note: self_explorer.py will handle app name prompting if not provided.
    # We are setting the root_dir to new_agent_dir to ensure paths are relative to NewAgent's root.
    # sys.argv manipulation is one way, but can be tricky. 
    # A cleaner way would be to refactor self_explorer.main to accept parameters.
    # Given self_explorer.py already uses argparse, let's try to make it callable.
    
    # We'll call self_explorer.main(), but it needs to parse its own args.
    # We need to ensure that when self_explorer.main() is called, 
    # it can correctly parse --app and --root_dir if we want to pass them from here.
    # For simplicity, we'll let self_explorer.py handle its own argument parsing
    # when its main() is called. If --app is not passed from command line to learn.py,
    # self_explorer.py will prompt for it.
    
    # To make self_explorer.py runnable when imported, its main() function should be callable.
    # And its argparse should work correctly. Let's ensure root_dir is correctly contextualized.
    # If args.root_dir is '.', when learn.py is run from NewAgent, '.' is NewAgent.
    # When self_explorer.py is called, its CWD is also NewAgent, so default '.' for its root_dir works.

    # Temporarily modify sys.argv for self_explorer's argparse
    original_argv = sys.argv
    simulated_argv = ["scripts/self_explorer.py"] # Script name
    if args.app:
        simulated_argv.extend(["--app", args.app])
    if args.root_dir:
         # Ensure root_dir is an absolute path from NewAgent perspective or relative to it.
         # If learn.py is in NewAgent, and root_dir is '.', it means NewAgent folder itself.
        simulated_argv.extend(["--root_dir", os.path.abspath(args.root_dir)])
    else:
        simulated_argv.extend(["--root_dir", new_agent_dir]) # Default to NewAgent dir

    sys.argv = simulated_argv
    
    try:
        print_with_color(f"Calling self_explorer.main() with simulated args: {sys.argv}", "yellow")
        self_explorer.main() # Call the main function from the imported module
    finally:
        sys.argv = original_argv # Restore original sys.argv

    print_with_color("Autonomous exploration process finished.", "blue")

if __name__ == "__main__":
    main_learn() 