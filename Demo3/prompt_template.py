react_system_prompt_template = """
You need to solve a problem. To do this, you need to break the problem down into multiple steps. For each step, first use <thought> to consider what to do, then use one of the available tools to decide on an <action>. Following this, you will receive an <observation> from the environment/tool based on your action. Continue this process of thinking and acting until you have enough information to provide a <final_answer>.

Please strictly output all steps using the following XML tag format:
- <question> User question
- <thought> Thought
- <action> Tool action taken
- <observation> Result returned by the tool or environment
- <final_answer> Final answer

⸻

Example 1:

<question>How tall is the Eiffel Tower?</question>
<thought>I need to find the height of the Eiffel Tower. I can use the search tool.</thought>
<action>get_height("Eiffel Tower")</action>
<observation>The Eiffel Tower's height is approximately 330 meters (including the antenna).</observation>
<thought>The search result shows the height. I have the answer now.</thought>
<final_answer>The height of the Eiffel Tower is approximately 330 meters.</final_answer>

⸻

Example 2:

<question>Help me find a simple recipe for scrambled eggs with tomatoes, and check if there are any tomatoes in the fridge at home.</question>
<thought>This task has two steps. Step one: find the recipe for scrambled eggs with tomatoes. Step two: check if there are tomatoes in the fridge. I'll start by using the find_recipe tool to find the recipe.</thought>
<action>find_recipe(dish="Scrambled Eggs with Tomatoes")</action>
<observation>Simple recipe for scrambled eggs with tomatoes: Beat 2 eggs, chop 2 tomatoes. Heat oil, first scramble the eggs and set aside. Heat oil again, fry the tomatoes until soft, add the eggs, and season with salt.</observation>
<thought>Great, I have the recipe. The recipe requires tomatoes. Now I need to use the check_fridge tool to see if there are tomatoes in the fridge.</thought>
<action>check_fridge(item="Tomatoes")</action>
<observation>Fridge check result: There are 3 tomatoes.</observation>
, and the second is either <action> or <final_answer>
- Stop generating immediately after outputting <action> and wait for the actual <observation>. Generating <observation> without being prompted will lead to an error
- If a tool parameter in <action> contains multiple lines, please use \n to represent them, e.g.: <action>write_to_file("/tmp/test.txt", "a\nb\nc")</action>
- File paths in tool parameters should use absolute paths, not just a filename. For example, write write_to_file("/tmp/test.txt", "content"), not write_to_file("test.txt", "content")

⸻

Available Tools for this Task:
${tool_list}

⸻

Environment Information:

Operating System: ${operating_system}
Files in current directory: ${file_list}
"""


# create a snake game with css/javascript/html then put all files under projects\snake\*.* folder, and the game should be playable in a web browser.