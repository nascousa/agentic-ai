# Execution Instructions

First, ensure you have **Python 3.12+** installed. Then create a virtual environment and install the required dependencies:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Next, in the current directory, rename **.env.example** to **.env** and enter the following content:

```
OPENROUTER_API_KEY=sk-or-v1-7fadb8550...
```

`sk-or-v1-7fadb8550...` should be the API Key you configured on **OpenRouter**. If you are not using OpenRouter, you can simply change the `baseUrl` in the code to use a different service.

Once you have confirmed that **Python** is successfully installed and dependencies are ready, navigate to the directory containing the current file and execute the following command to start:

```bash
python agent.py [PROJECT_DIRECTORY]
```

For example:
```bash
python agent.py project
```