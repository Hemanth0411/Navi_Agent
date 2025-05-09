import argparse
import os
import sys
import time
import signal

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
from scripts.cleanup import cleanup_exploration_data, verify_cleanup
from scripts.and_controller import launch_app_by_package

def signal_handler(signum, frame):
    """Handle interruption signals gracefully"""
    print_with_color("\nReceived interruption signal. Stopping exploration...", "yellow")
    raise KeyboardInterrupt()

def main_learn():
    # Set up signal handlers for graceful interruption
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="NewAgent - Autonomous App Exploration")
    parser.add_argument("--package", type=str, required=True, help="Package name of the target application (e.g., com.android.chrome)")
    parser.add_argument("--app_name", type=str, required=True, help="Name of the application (e.g., Chrome)")
    parser.add_argument("--description", type=str, required=True, help="Description of the app's purpose and functionality")
    parser.add_argument("--root_dir", type=str, default=".", help="Root directory for the agent's operation")
    args = parser.parse_args()

    # Create app directory using app name
    work_dir = os.path.join(args.root_dir, "apps")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    app_dir = os.path.join(work_dir, args.app_name)
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)

    print_with_color(f"Starting exploration of {args.app_name} ({args.package})", "blue")
    print_with_color(f"App Description: {args.description}", "yellow")

    # Launch the app using package name
    try:
        print_with_color(f"Launching {args.app_name}...", "blue")
        launch_app_by_package(args.package)
        print_with_color(f"Successfully launched {args.app_name}", "green")
        
        # Give the app a moment to fully launch
        time.sleep(2)
    except Exception as e:
        print_with_color(f"Error launching app: {e}", "red")
        return

    # Start exploration
    try:
        print_with_color("Starting autonomous exploration...", "blue")
        print_with_color("Press Ctrl+C to stop exploration", "yellow")
        
        # Call self_explorer with the correct parameters
        self_explorer.main(
            app=args.app_name,
            root_dir=args.root_dir,
            package_name=args.package,
            app_description=args.description
        )
    except KeyboardInterrupt:
        print_with_color("\nExploration stopped by user", "yellow")
    except Exception as e:
        print_with_color(f"Error during exploration: {e}", "red")
    finally:
        # print_with_color("Cleaning up exploration data...", "yellow")
        # cleanup_exploration_data(args.app_name)
        # if verify_cleanup(args.app_name):
        #     print_with_color("Cleanup successful", "green")
        # else:
        #     print_with_color("Cleanup verification failed", "red")
        print_with_color("Exploration completed", "blue")

if __name__ == "__main__":
    main_learn() 