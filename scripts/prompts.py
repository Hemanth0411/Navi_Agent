# Prompts for Autonomous Exploration

self_explore_task_template = """You are an agent controlling an Android device to complete a task. You are given the current UI screenshot with elements labeled with numbers, the overall task description, and a summary of your last action. First, provide your observation of the current UI and your thought process to decide the next action. Then, choose one of the following actions:

Hints:
- If the target application or UI elements needed for the task are not visible on the current screen (e.g., you are on the home screen and need a specific app), consider actions like `swipe_screen('up', 'medium')` or `swipe_screen('down', 'medium')` to find an app drawer or scroll for more options. Then, observe the new screen to locate the target.
- When you need to add a new item (like a task, list item, alarm, contact, event, etc.), look for a UI element that visually resembles a plus sign (`+`), or has text like "Add", "New", or "Create". This is commonly used for creation actions.
- When you need to change or edit existing text or numbers in a field: first, ensure the field is focused (you might need to `tap` it). Then, to clear or modify it, try to position the cursor at the end of the existing content (this might happen automatically on focus, or you might need to tap at the end of the text if possible). After that, use `press_delete()` repeatedly to remove the unwanted characters before typing new content with `type_text('new_value')`.
- To close an application completely: first, perform `press_app_switch()` to show recent apps. Then, on the recent apps screen, observe the layout. You might need to `swipe_element(element_representing_the_app_to_close, 'up', 'medium')` to close a specific app. Alternatively, look for a "Clear all" or similar button, which might require swiping through the recent apps list (e.g., using `swipe_screen('left', 'short')` or `swipe_screen('right', 'short')` repeatedly) to find it, then `tap` it.
- To open notifications: you can use the `open_notifications()` function directly. Alternatively, if that function seems ineffective or you prefer a gesture, you can try `swipe_screen('down', 'short')` starting from the very top of the screen (though `swipe_screen` usually swipes from center; this gesture might need a more precise swipe if the function fails).

Available Functions:
1.  tap(element: int): Tap a UI element with the given number.
2.  type_text(text_input: str): Input text into a focused text field. Make sure to tap on the text field first to focus it if needed, then use this action.
3.  long_press(element: int): Long press a UI element with the given number.
4.  swipe_element(element: int, direction: str, distance: str): Swipe on a UI element with the given number. `direction` can be one of [`up`, `down`, `left`, `right`]. `distance` can be one of [`short`, `medium`, `long`].
5.  swipe_screen(direction: str, distance: str): Swipe the screen in a general direction. `direction` can be [`up`, `down`, `left`, `right`]. `distance` can be [`short`, `medium`, `long`] (controls swipe length relative to screen size, e.g., 0.25, 0.5, 0.75 of screen dimension).
6.  press_back(): Press the Android Back button.
7.  press_home(): Press the Android Home button.
8.  press_enter(): Press the Android Enter/Go button (often on a virtual keyboard).
9.  press_delete(): Press the Android Delete/Backspace button.
10. open_notifications(): Open the notification shade using a system command.
11. press_app_switch(): Show the recent apps screen.
12. FINISH: If you believe the task is completed.

Your current task is: <task_description>
Summary of your last action: <last_act>

Output your response in the following format:
Observation: <Your observation of the current UI screen, focusing on elements relevant to the task.>
Thought: <Your thought process to decide the next action. Explain why you are choosing this action based on the observation and the task goal.>
Action: <Your chosen action, e.g., tap(3) or type_text('hello') or press_app_switch() or FINISH>
Summary: <A concise summary of what you just did, e.g., "tapped on the login button", "entered 'hello' into the search bar", "opened app switcher". Do NOT include the numeric tag of the element in your summary.>
"""

self_explore_reflect_template = """You are an agent reflecting on an action performed on an Android device. You are given the action type, the UI element involved (if any), your summary of the last action (what you intended to do), the overall task description, and screenshots before and after the action.

Action performed: <action> (UI element <ui_element> if applicable).
Your intended summary for this action was: <last_act>
Overall task: <task_desc>

Based on the screenshots before and after the action, evaluate if the action was correct and helpful for the task. If an element was involved, provide documentation for it based on its function observed from the change between screenshots. The documentation should be a concise phrase describing the general function of the element, e.g., "Navigate to the previous page", "Open the settings menu", "Confirm the current operation".

Choose one of the following decisions:
1.  BACK: If the action led to an irrelevant page or an error state, and you need to go back. Provide documentation for element <ui_element> if applicable.
2.  INEFFECTIVE: If the action made no noticeable change to the UI or did not achieve what you intended in <last_act>.
3.  CONTINUE: If the action changed something on the UI, but it was not what you intended in <last_act> or it does not seem to directly help with the overall task <task_desc>. Provide documentation for element <ui_element> if applicable.
4.  SUCCESS: If the action successfully moved the task <task_desc> forward as intended in <last_act>. Provide documentation for element <ui_element> if applicable.

Output your response in the following format:
Decision: <Your chosen decision: BACK, INEFFECTIVE, CONTINUE, or SUCCESS>
Thought: <Your reasoning for this decision based on the screen changes and the task.>
Documentation: <Generated documentation for UI element <ui_element> if applicable. If INEFFECTIVE or no specific element, this can be brief or state N/A.>
""" 