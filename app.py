from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

app = Flask(__name__)
socketio = SocketIO(app)

# Initialize LLaMA model and prompt template
model = OllamaLLM(model="llama3.2")
summarize_prompt = ChatPromptTemplate.from_template("""
Summarize the group chat in an extremely brief bullet-point format, following these guidelines:

- Use new lines for each bullet point and section.
- Be concise and direct and very short.

Topic: 
   - State the main topic of the entire chat.
Problems Identified: 
   - List any significant problems discussed.
User Contributions:
   - User: Summarize key points from User 1's messages.
   - User: Summarize key points from User 2's messages.
   - User: Summarize key points from User 3's messages.
Resolution: 
   - Briefly explain how the problems were addressed.
Summary: 
   - Provide a short conclusion about the chat in one or two lines.
   
Chat Context:
{context}
""")

chat_prompt = ChatPromptTemplate.from_template("""
Answer the question below.

Here is the conversation history: {context}

Question: {question}

Answer:
""")

# Store chat history and active users
chat_history = []
active_users = set()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('send_message')
def handle_message(data):
    username = data['username']
    message = data['message']
    
    # Add the user to active users
    active_users.add(username)
    
    chat_history.append(f"{username}: {message}")
    emit('receive_message', {'message': f"{username}: {message}", 'user': username}, broadcast=True)
    emit('user_list', list(active_users), broadcast=True)

@socketio.on('ai_prompt')
def handle_ai_prompt(data):
    username = data['username']
    context = "\n".join(chat_history)
    
    # Format the prompt using the chat prompt template
    formatted_prompt = chat_prompt.format(context=context, question=data['question'])
    
    # Get the AI response as a whole
    result = model.invoke(formatted_prompt)
    
    # Emit the AI response only to the specific user who asked
    emit('receive_message', {'message': f"AI: {result}", 'user': 'AI'}, room=request.sid)

@socketio.on('summarize_chat')
def handle_summarize(data):
    context = "\n".join(chat_history)
    
    # Format the prompt for summarization
    formatted_prompt = summarize_prompt.format(context=context)
    
    # Invoke the model for a summary
    summary = model.invoke(formatted_prompt)
    emit('receive_message', {'message': f"Summary: {summary}", 'user': 'AI'}, room=request.sid)

@socketio.on('connect')
def handle_connect():
    emit('user_list', list(active_users))

@socketio.on('disconnect')
def handle_disconnect():
    # Logic to remove user from active_users can be added here
    pass

if __name__ == '__main__':
    socketio.run(app)
