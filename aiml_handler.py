import os
import pyaiml21 as aiml

aiml_directory = "C:/Users/HP/Downloads/backend/aimlfile"

def load_aiml_files(aiml_directory):
    aim_files = [f for f in os.listdir(aiml_directory) if f.endswith('.aiml')]
    if not aim_files:
        raise FileNotFoundError(f"No AIML files found in '{aiml_directory}'.")

    kernel = aiml.Kernel()
    for file in aim_files:
        file_path = os.path.join(aiml_directory, file)
        kernel.learn(file_path)
        print(f"Loaded '{file_path}' successfully.")
    return kernel

def aiml_response(user_input, kernel):
    try:
        user_input = str(user_input)
        kernel.setBotPredicate("username", "Ali")
        response = kernel.respond(user_input, "user1")  # Provide a user_id, e.g., "user1"
        if response:
            return str(response)
        else:
            return "I'm not sure how to respond to that."
    except Exception as e:
        print("Response Error:", e)
        return "An error occurred while generating response. Please try again later."

# Example usage:
if __name__ == "__main__":
    kernel = load_aiml_files(aiml_directory)
    user_input = "Hello"
    print(aiml_response(user_input, kernel))
