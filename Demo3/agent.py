import ast
import inspect
import os
import re
from string import Template
from typing import List, Callable, Tuple

import click
from dotenv import load_dotenv
from openai import OpenAI
import platform
from colorama import init, Fore, Back, Style

from prompt_template import react_system_prompt_template

# Initialize colorama for cross-platform color support
init(autoreset=True)


class ReActAgent:
    def __init__(self, tools: List[Callable], model: str, project_directory: str):
        self.tools = {func.__name__: func for func in tools}
        self.model = model
        self.project_directory = project_directory
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=ReActAgent.get_api_key(),
        )

    def run(self, user_input: str):
        messages = [
            {"role": "system", "content": self.render_system_prompt(react_system_prompt_template)},
            {"role": "user", "content": f"<question>{user_input}</question>"}
        ]

        while True:

            # Request the model
            content = self.call_model(messages)

            # Detect Thought
            thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)
            if thought_match:
                thought = thought_match.group(1)
                print(f"\n\n{Fore.CYAN}💭 Thought:{Style.RESET_ALL} {Fore.WHITE}{thought}{Style.RESET_ALL}")

            # Check if the model output a Final Answer. If so, return it directly
            if "<final_answer>" in content.lower():
                # Try to extract final answer with more flexible regex
                final_answer = re.search(r"<final_answer>(.*?)</final_answer>", content, re.DOTALL | re.IGNORECASE)
                if final_answer:
                    answer = final_answer.group(1).strip()
                    return answer
                else:
                    # If regex fails, try to extract content after <final_answer> tag manually
                    try:
                        start_tag_pos = content.lower().find("<final_answer>")
                        if start_tag_pos != -1:
                            content_after_tag = content[start_tag_pos + len("<final_answer>"):]
                            end_tag_pos = content_after_tag.lower().find("</final_answer>")
                            if end_tag_pos != -1:
                                answer = content_after_tag[:end_tag_pos].strip()
                                return answer
                            else:
                                # No closing tag found, take everything after opening tag until end
                                answer = content_after_tag.strip()
                                # Remove any trailing XML or extra content
                                lines = answer.split('\n')
                                clean_lines = []
                                for line in lines:
                                    if not line.strip().startswith('<') or line.strip().startswith('</final_answer>'):
                                        clean_lines.append(line)
                                    else:
                                        break
                                answer = '\n'.join(clean_lines).strip()
                                if answer:
                                    return answer
                    except Exception as e:
                        print(f"\n\n{Fore.YELLOW}Debug: Error parsing final answer: {str(e)}{Style.RESET_ALL}")
                    
                    print(f"\n\n{Fore.RED}🤖 Model output contains <final_answer> but format is incorrect:{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{content}{Style.RESET_ALL}")
                    return "Error: Malformed final answer format"

            # Detect Action
            action_match = re.search(r"<action>(.*?)</action>", content, re.DOTALL)
            if not action_match:
                print(f"\n\n{Fore.RED}❌ Model did not output a valid <action> tag.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Model output:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{content}{Style.RESET_ALL}")
                print(f"\n{Fore.YELLOW}Expected format: <action>tool_name(arg1, arg2)</action>{Style.RESET_ALL}")
                return "Error: Model did not provide a valid action format."
            action = action_match.group(1)
            tool_name, args = self.parse_action(action)

            print(f"\n\n{Fore.YELLOW}🔧 Action:{Style.RESET_ALL} {Fore.GREEN}{tool_name}({', '.join(args)}){Style.RESET_ALL}")
            # Only terminal commands need to prompt the user, other tools are executed directly
            should_continue = input(f"\n\n{Fore.MAGENTA}Should I continue? (Y/N) {Style.RESET_ALL}") if tool_name == "run_terminal_command" else "y"
            if should_continue.lower() != 'y':
                print(f"\n\n{Fore.RED}Operation cancelled.{Style.RESET_ALL}")
                return "Operation cancelled by user"

            try:
                observation = self.tools[tool_name](*args)
            except Exception as e:
                observation = f"Tool execution error: {str(e)}"
            print(f"\n\n{Fore.BLUE}🔍 Observation:{Style.RESET_ALL} {Fore.LIGHTBLUE_EX}{observation}{Style.RESET_ALL}")
            obs_msg = f"<observation>{observation}</observation>"
            messages.append({"role": "user", "content": obs_msg})


    def get_tool_list(self) -> str:
        """Generates a tool list string, including function signatures and brief descriptions"""
        tool_descriptions = []
        for func in self.tools.values():
            name = func.__name__
            signature = str(inspect.signature(func))
            doc = inspect.getdoc(func)
            tool_descriptions.append(f"- {name}{signature}: {doc}")
        return "\n".join(tool_descriptions)

    def render_system_prompt(self, system_prompt_template: str) -> str:
        """Renders the system prompt template, replacing variables"""
        tool_list = self.get_tool_list()
        file_list = ", ".join(
            os.path.abspath(os.path.join(self.project_directory, f))
            for f in os.listdir(self.project_directory)
        )
        return Template(system_prompt_template).substitute(
            operating_system=self.get_operating_system_name(),
            tool_list=tool_list,
            file_list=file_list
        )

    @staticmethod
    def get_api_key() -> str:
        """Load the API key from an environment variable."""
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not found. Please set it in the .env file.")
        return api_key

    def call_model(self, messages):
        print(f"\n\n{Fore.YELLOW}Requesting model, please wait...{Style.RESET_ALL}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            content = response.choices[0].message.content
            messages.append({"role": "assistant", "content": content})
            return content
        except Exception as e:
            if "402" in str(e) or "credits" in str(e).lower():
                print(f"\n{Fore.RED}❌ Error: Insufficient credits on OpenRouter account.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please visit https://openrouter.ai/settings/credits to add more credits.{Style.RESET_ALL}")
                raise SystemExit(1)
            else:
                print(f"\n{Fore.RED}❌ API error: {str(e)}{Style.RESET_ALL}")
                raise SystemExit(1)

    def parse_action(self, code_str: str) -> Tuple[str, List[str]]:
        match = re.match(r'(\w+)\((.*)\)', code_str, re.DOTALL)
        if not match:
            raise ValueError("Invalid function call syntax")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # Manually parse arguments, specifically handling strings that contain multiple lines
        args = []
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0
        
        while i < len(args_str):
            char = args_str[i]
            
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0:
                    # Encountered a top-level comma, end of current argument
                    args.append(self._parse_single_arg(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        # Add the last argument
        if current_arg.strip():
            args.append(self._parse_single_arg(current_arg.strip()))
        
        return func_name, args
    
    def _parse_single_arg(self, arg_str: str):
        """Parses a single argument"""
        arg_str = arg_str.strip()
        
        # If it's a string literal
        if (arg_str.startswith('"') and arg_str.endswith('"')) or \
           (arg_str.startswith("'") and arg_str.endswith("'")):
            # Remove outer quotes
            inner_str = arg_str[1:-1]
            
            # For file paths, don't process escape sequences - just clean up line breaks
            # Check if this looks like a file path (contains common path indicators)
            if ('/' in inner_str or '\\' in inner_str or 
                inner_str.startswith(('./', '../', '~/', 'C:', '/')) or
                ':\\' in inner_str):
                # This looks like a file path - clean up any line breaks but don't process other escapes
                inner_str = inner_str.replace('\n', '').replace('\r', '')
                # Handle basic quote escaping only
                inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
                return inner_str
            else:
                # Not a file path - handle all escape characters normally
                inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
                inner_str = inner_str.replace('\\n', '\n').replace('\\t', '\t')
                inner_str = inner_str.replace('\\r', '\r').replace('\\\\', '\\')
                return inner_str
        
        # Try to parse other types using ast.literal_eval
        try:
            return ast.literal_eval(arg_str)
        except (SyntaxError, ValueError):
            # If parsing fails, return the original string
            return arg_str

    def get_operating_system_name(self):
        os_map = {
            "Darwin": "macOS",
            "Windows": "Windows",
            "Linux": "Linux"
        }

        return os_map.get(platform.system(), "Unknown")


def read_file(file_path):
    """Used to read file content"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def write_to_file(file_path, content):
    """Writes the specified content to the specified file"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content.replace("\\n", "\n"))
    return "Write successful"

def run_terminal_command(command):
    """Used to execute a terminal command"""
    import subprocess
    run_result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return "Execution successful" if run_result.returncode == 0 else run_result.stderr

@click.command()
@click.argument('project_directory',
                type=click.Path(exists=True, file_okay=False, dir_okay=True))
def main(project_directory):
    project_dir = os.path.abspath(project_directory)

    tools = [read_file, write_to_file, run_terminal_command]
    agent = ReActAgent(tools=tools, model="openai/gpt-4o", project_directory=project_dir)

    task = input("\n\nPlease enter the task: ")

    final_answer = agent.run(task)

    print(f"\n\n{Fore.MAGENTA}✅ Final Answer:{Style.RESET_ALL} {Fore.MAGENTA}{final_answer}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()