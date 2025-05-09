# Prompts for Autonomous App Exploration

self_explore_task_template = """You are an agent controlling an Android device to explore and understand an app. You are given:
1. The package name and app name of the target application
2. A description of what the app is about and its main purpose
3. The current UI screenshot with elements labeled with numbers
4. A summary of your last action

Your goal is to systematically explore the app's features and functionality based on the provided description. First, provide your observation of the current UI and your thought process to decide the next action. Then, choose one of the following actions:

Hints for App Exploration:
- If you're not in the target app, use `press_home()` to return to the home screen, then look for the app icon or use the app drawer.
- When exploring features, look for common UI patterns:
  * Plus (+) icons or "Add"/"New" buttons for creating items
  * Three dots (⋮) or gear icons for settings
  * Search icons for search functionality
  * Menu icons for navigation
  * Back arrows or the back button to return to previous screens

- For text input:
  * First `tap` the input field to focus it
  * Use `press_delete()` to clear existing text if needed
  * Then use `type_text()` to enter new text
  * Use `press_enter()` to submit

- For navigation:
  * Use `swipe_screen()` to scroll through content
  * Use `swipe_element()` for scrollable elements like lists
  * Use `press_back()` to return to previous screens
  * Use `press_home()` to return to home screen

- For app control:
  * Use `press_app_switch()` to see recent apps
  * Use `open_notifications()` to check notifications
  * Use `long_press()` to access context menus

Available Functions:
1. tap(element: int): Tap a UI element with the given number
2. type_text(text_input: str): Input text into a focused text field
3. long_press(element: int): Long press a UI element with the given number
4. swipe_element(element: int, direction: str, distance: str): Swipe on a UI element
   - direction: ['up', 'down', 'left', 'right']
   - distance: ['short', 'medium', 'long']
5. swipe_screen(direction: str, distance: str): Swipe the screen in a general direction
6. press_back(): Press the Android Back button
7. press_home(): Press the Android Home button
8. press_enter(): Press the Android Enter/Go button
9. press_delete(): Press the Android Delete/Backspace button
10. open_notifications(): Open the notification shade
11. press_app_switch(): Show the recent apps screen
12. FINISH: If you believe you've explored the main features of the app

App Information:
Package Name: <package_name>
App Name: <app_name>
App Description: <app_description>
Last Action: <last_act>

Output your response in the following format:
Observation: <Your observation of the current UI screen, focusing on elements relevant to the app's purpose>
Thought: <Your thought process to decide the next action, considering the app's description and purpose>
Action: <Your chosen action, e.g., tap(3) or type_text('hello') or press_app_switch() or FINISH>
Summary: <A concise summary of what you just did, focusing on the feature being explored>
"""

self_explore_reflect_template = """You are an agent reflecting on an action performed while exploring an Android app. You are given:
1. The action type and UI element involved (if any)
2. Your summary of the last action
3. The app's package name, name, and description
4. Screenshots before and after the action

Action performed: <action> (UI element <ui_element> if applicable)
Your intended summary for this action was: <last_act>
App Information:
Package Name: <package_name>
App Name: <app_name>
App Description: <app_description>

Based on the screenshots before and after the action, evaluate if the action was correct and helpful for understanding the app's features. If an element was involved, provide documentation for it based on its function observed from the change between screenshots.

Choose one of the following decisions:
1. BACK: If the action led to an irrelevant page or an error state, and you need to go back. Provide documentation for element <ui_element> if applicable.
2. INEFFECTIVE: If the action made no noticeable change to the UI or did not achieve what you intended in <last_act>.
3. CONTINUE: If the action changed something on the UI, but it was not what you intended in <last_act> or it does not seem to directly help with understanding the app's features. Provide documentation for element <ui_element> if applicable.
4. SUCCESS: If the action successfully helped understand a feature of the app as intended in <last_act>. Provide documentation for element <ui_element> if applicable.

Output your response in the following format:
Decision: <Your chosen decision: BACK, INEFFECTIVE, CONTINUE, or SUCCESS>
Thought: <Your reasoning for this decision based on the screen changes and the app's purpose>
Documentation: <Generated documentation for UI element <ui_element> if applicable. If INEFFECTIVE or no specific element, this can be brief or state N/A>
"""

# Additional templates for specific actions
tap_doc_template = """I will give you the screenshot of a mobile app before and after tapping the UI element labeled with the number <ui_element>. The action was performed while exploring the app <app_name> (<package_name>), which is described as: <app_description>. Your task is to describe the functionality of the UI element concisely in one or two sentences, focusing on its role in the app's features. Never include the numeric tag of the UI element in your description."""

text_doc_template = """I will give you the screenshot of a mobile app before and after typing in the input area labeled with the number <ui_element>. The action was performed while exploring the app <app_name> (<package_name>), which is described as: <app_description>. Your task is to describe the functionality of the input area concisely in one or two sentences, focusing on its role in the app's features. Never include the numeric tag of the UI element in your description."""

long_press_doc_template = """I will give you the screenshot of a mobile app before and after long pressing the UI element labeled with the number <ui_element>. The action was performed while exploring the app <app_name> (<package_name>), which is described as: <app_description>. Your task is to describe the functionality of the UI element concisely in one or two sentences, focusing on its role in the app's features. Never include the numeric tag of the UI element in your description."""

swipe_doc_template = """I will give you the screenshot of a mobile app before and after swiping <swipe_dir> the UI element labeled with the number <ui_element>. The action was performed while exploring the app <app_name> (<package_name>), which is described as: <app_description>. Your task is to describe the functionality of the UI element concisely in one or two sentences, focusing on its role in the app's features. Never include the numeric tag of the UI element in your description."""

# Feature extraction prompt
feature_extraction_prompt = """You are an agent that is trained to analyze mobile applications. Your task is to identify the key features that should be explored in the given app.

App Description: {description}

Based on this description, identify the key features that should be explored. For each feature, provide:
1. Feature name
2. Expected behavior
3. How to verify it works
4. Potential edge cases

Your output should be in the following format:

Features to Explore:
1. <feature_name>
   - Expected behavior: <description>
   - Verification method: <steps>
   - Edge cases: <list>

2. <feature_name>
   - Expected behavior: <description>
   - Verification method: <steps>
   - Edge cases: <list>

[Continue for all identified features]

Focus on:
1. Core functionality
2. User interactions
3. Data management
4. Navigation patterns
5. Error handling
6. Performance aspects

Be thorough but concise. Each feature should be clearly defined and testable.

IMPORTANT: 
1. Do not include any placeholder text or requests for more information
2. Base your analysis solely on the provided app description
3. If the description is insufficient, return "INSUFFICIENT_DESCRIPTION" as the first line
4. Each feature should be a concrete, testable functionality"""

# Screen analysis prompt
screen_analysis_prompt = """You are an agent that is trained to analyze mobile app screens. You will be given a screenshot of the current screen with labeled interactive elements. Your task is to analyze the screen and identify available features and actions.

The current screen shows: <screen_state>

The interactive elements are labeled with numbers. For each element, provide:
1. Element number
2. Element type (button, text field, etc.)
3. Visible text or label
4. Potential action
5. Expected outcome

Your output should be in the following format:

Screen Analysis:
1. Element <number>
   - Type: <element_type>
   - Label: <visible_text>
   - Action: <possible_action>
   - Expected: <outcome>

2. Element <number>
   - Type: <element_type>
   - Label: <visible_text>
   - Action: <possible_action>
   - Expected: <outcome>

[Continue for all interactive elements]

Screen Context:
- Current screen appears to be: <screen_type>
- Main purpose: <purpose>
- Available actions: <list_of_actions>
- Navigation options: <navigation_options>
- Loading state: <is_loading/not_loading>
  * If loading, estimate wait time: <estimated_seconds>
  * Loading indicators present: <yes/no>
  * Loading progress visible: <yes/no>

Focus on:
1. Interactive elements
2. Navigation patterns
3. Available features
4. User input areas
5. Action buttons
6. Status indicators
7. Loading states and progress

Be thorough but concise. Each element should be clearly identified and its purpose understood. Pay special attention to loading states and progress indicators."""

# Decision making prompt
decision_making_prompt = """You are an agent that is trained to perform tasks on a smartphone. You will be given a smartphone screenshot. The interactive UI elements on the screenshot are labeled with numeric tags starting from 1. The numeric tag of each interactive element is located in the center of the element.

You can call the following functions to control the smartphone:

1. tap(x: int, y: int)
This function is used to tap a specific coordinate on the smartphone screen.
"x" and "y" are the coordinates where you want to tap.
A simple use case can be tap(500, 800), which taps at coordinates (500, 800).

2. swipe(start_x: int, start_y: int, end_x: int, end_y: int)
This function is used to perform a swipe gesture on the screen.
"start_x" and "start_y" are the starting coordinates.
"end_x" and "end_y" are the ending coordinates.
A simple use case can be swipe(500, 800, 500, 200), which swipes from (500, 800) to (500, 200).

3. back()
This function is used to press the back button.

4. home()
This function is used to press the home button.

5. wait(seconds: int)
This function is used to wait for a specified number of seconds, typically when the screen is loading or transitioning.
"seconds" is the number of seconds to wait.
A simple use case can be wait(3), which waits for 3 seconds.

The task you need to complete is to <task_description>. Your past actions to proceed with this task are summarized as follows: <last_act>

Now, given the following labeled screenshot, you need to think and call the function needed to proceed with the task. Your output should include three parts in the given format:

Observation: <Describe what you observe in the image>
Thought: <To complete the given task, what is the next step I should do>
Action: <The function call with the correct parameters to proceed with the task. If you believe the task is completed or there is nothing to be done, you should output FINISH. You cannot output anything else except a function call or FINISH in this field.>
Summary: <Summarize your past actions along with your latest action in one or two sentences. Do not include the numeric tag in your summary>

IMPORTANT RULES:
1. The Action field MUST contain ONLY one of these exact formats:
   - tap(x, y)
   - swipe(start_x, start_y, end_x, end_y)
   - back()
   - home()
   - wait(seconds)
   - FINISH
2. Do not include any explanatory text in the Action field
3. Do not use any other action types
4. Make sure all parameters are valid integers
5. Do not include any other text or formatting in the Action field"""

# Feature exploration completion prompt
exploration_completion_prompt = """Review the exploration progress and determine if all features have been explored.
Consider:
1. Features identified from description
2. Features found during exploration
3. Current screen state
4. Exploration history

Features to Explore: {features_to_explore}
Explored Features: {explored_features}
Current State: {current_state}
Exploration History: {exploration_history}

Return either:
- CONTINUE: if there are more features to explore
- COMPLETE: if all features have been explored
""" 