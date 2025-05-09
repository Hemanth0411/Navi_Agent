import subprocess

# App details
APP_INFO = {
    "package_name": "com.mdiwebma.tasks",
    "app_name": "Checklist",
    "description": """Checklist is a free Android app developed by mdiwebma.com. It falls under the category of Business & Productivity and offers a range of features to help users efficiently manage their tasks and projects.
    The app allows users to create project plans and easily create new tasks or task groups. With just a click of a button, users can write main tasks or sub-tasks all at once.
    The app also provides the option to edit or delete selected tasks or task groups, making it easy to make changes as needed.
    One of the standout features of Checklist is the ability to create an unlimited hierarchy task tree viewer. This allows users to organize their tasks in a hierarchical structure, making it easier to visualize and manage complex projects.
    Users can also customize the appearance of their tasks by highlighting the task name color, making it bold or italicized.
    Checklist also offers convenient drag and drop functionality, allowing users to easily move selected sub-tasks within their task groups.
    This makes it simple to rearrange tasks and adjust the project timeline as needed. Additionally, users can expand or collapse sub-tasks to focus on specific areas of their project.
    The app also includes a hashtag feature for easy searching and organization of tasks. Users can add hashtags to their tasks, making it simple to find specific tasks or group related tasks together.
    In conclusion, Checklist is a powerful task management app for Android that offers a wide range of features to help users stay organized and efficient. Whether you're managing personal projects or working on a team, Checklist provides the tools you need to effectively manage your tasks and projects."""
}

def main():
    # Construct and run the command
    command = [
        "python", "learn.py",
        "--package", APP_INFO["package_name"],
        "--app_name", APP_INFO["app_name"],
        "--description", APP_INFO["description"]
    ]
    
    subprocess.run(command)

if __name__ == "__main__":
    main() 



# python learn.py --package com.mdiwebma.tasks --app_name Checklist --description "Checklist is a free Android app developed by mdiwebma.com. It falls under the category of Business & Productivity and offers a range of features to help users efficiently manage their tasks and projects."