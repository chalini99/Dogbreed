import subprocess

MODEL = "llama3.1"

def ask_bot(question):
    try:
        # Construct the prompt
        full_prompt = f"Answer very shortly and clearly:\n\nUser: {question}\nAI:"

        # Run Ollama model
        result = subprocess.run(
            ["ollama", "run", MODEL, full_prompt],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return "⚠️ Ollama error: Make sure Ollama is running."

        return result.stdout.strip()

    except Exception as e:
        return f"⚠️ Chatbot error: {e}"
