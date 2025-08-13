# main.py - FastAPI Application
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import socketio
import asyncio
from celery.result import AsyncResult
from pydantic import BaseModel
from typing import Optional
import uuid

# Import Celery app
from celery_app import celery_app
from tasks import process_long_task, send_email_task

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['*']
)

# Create FastAPI app
app = FastAPI(title="FastAPI Celery Socket.IO Demo")

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Models
class TaskRequest(BaseModel):
    task_name: str
    duration: int = 10
    email: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# In-memory storage untuk demo (production: gunakan database)
active_connections = {}

@app.get("/", response_class=HTMLResponse)
async def get_home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Celery Socket.IO Demo</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { margin: 20px 0; }
            .task-form { background: #f5f5f5; padding: 20px; border-radius: 5px; }
            .task-list { background: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
            .task-item { margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 3px; }
            .status { font-weight: bold; }
            .pending { color: orange; }
            .success { color: green; }
            .failure { color: red; }
            .progress { color: blue; }
            input, button { margin: 5px; padding: 8px; }
            button { background: #007cba; color: white; border: none; border-radius: 3px; cursor: pointer; }
            button:hover { background: #005a85; }
        </style>
    </head>
    <body>
        <h1>FastAPI + Celery + Socket.IO Demo</h1>
        
        <div class="container">
            <div class="task-form">
                <h3>Submit New Task</h3>
                <input type="text" id="taskName" placeholder="Task Name" value="Sample Task">
                <input type="number" id="duration" placeholder="Duration (seconds)" value="10" min="1" max="60">
                <input type="email" id="email" placeholder="Email (optional)">
                <button onclick="submitTask()">Submit Long Task</button>
                <button onclick="submitEmailTask()">Submit Email Task</button>
            </div>
        </div>

        <div class="container">
            <div class="task-list">
                <h3>Task Status (Real-time)</h3>
                <div id="tasks"></div>
            </div>
        </div>

        <script>
            const socket = io();
            const tasks = {};

            socket.on('connect', function() {
                console.log('Connected to server');
                document.getElementById('tasks').innerHTML += '<div>✅ Connected to server</div>';
            });

            socket.on('task_update', function(data) {
                console.log('Task update:', data);
                updateTaskDisplay(data);
            });

            async function submitTask() {
                const taskName = document.getElementById('taskName').value;
                const duration = document.getElementById('duration').value;
                
                const response = await fetch('/submit-task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_name: taskName,
                        duration: parseInt(duration)
                    })
                });
                
                const result = await response.json();
                console.log('Task submitted:', result);
                
                // Add to display
                tasks[result.task_id] = result;
                updateTaskDisplay({
                    task_id: result.task_id,
                    status: 'PENDING',
                    message: 'Task submitted and queued'
                });
            }

            async function submitEmailTask() {
                const email = document.getElementById('email').value;
                if (!email) {
                    alert('Please enter an email address');
                    return;
                }
                
                const response = await fetch('/submit-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_name: 'Send Email',
                        email: email
                    })
                });
                
                const result = await response.json();
                console.log('Email task submitted:', result);
                
                tasks[result.task_id] = result;
                updateTaskDisplay({
                    task_id: result.task_id,
                    status: 'PENDING',
                    message: 'Email task queued'
                });
            }

            function updateTaskDisplay(data) {
                const taskDiv = document.getElementById('task-' + data.task_id) || createTaskDiv(data.task_id);
                taskDiv.innerHTML = `
                    <div><strong>Task ID:</strong> ${data.task_id}</div>
                    <div><strong>Status:</strong> <span class="status ${data.status.toLowerCase()}">${data.status}</span></div>
                    <div><strong>Message:</strong> ${data.message}</div>
                    <div><strong>Time:</strong> ${new Date().toLocaleTimeString()}</div>
                    ${data.result ? '<div><strong>Result:</strong> ' + JSON.stringify(data.result) + '</div>' : ''}
                `;
            }

            function createTaskDiv(taskId) {
                const div = document.createElement('div');
                div.id = 'task-' + taskId;
                div.className = 'task-item';
                document.getElementById('tasks').appendChild(div);
                return div;
            }
        </script>
    </body>
    </html>
    """

@app.post("/submit-task", response_model=TaskResponse)
async def submit_task(task_request: TaskRequest):
    """Submit a long-running task to Celery"""
    task_id = str(uuid.uuid4())
    
    # Submit task to Celery
    celery_task = process_long_task.apply_async(
        args=[task_request.task_name, task_request.duration],
        task_id=task_id
    )
    
    return TaskResponse(
        task_id=task_id,
        status="PENDING",
        message="Task submitted successfully"
    )

@app.post("/submit-email", response_model=TaskResponse)
async def submit_email_task(task_request: TaskRequest):
    """Submit an email task to Celery"""
    task_id = str(uuid.uuid4())
    
    celery_task = send_email_task.apply_async(
        args=[task_request.email, "Test Email", "This is a test email from Celery!"],
        task_id=task_id
    )
    
    return TaskResponse(
        task_id=task_id,
        status="PENDING",
        message="Email task submitted successfully"
    )

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

# Socket.IO Events
@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")
    active_connections[sid] = True

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")
    active_connections.pop(sid, None)

# Background task to monitor Celery tasks
async def monitor_tasks():
    """Monitor task status and send updates via Socket.IO"""
    while True:
        try:
            # Dalam production, sebaiknya gunakan database untuk tracking tasks
            # Ini hanya contoh sederhana
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error in task monitor: {e}")
            await asyncio.sleep(5)

# Start background monitor when app starts
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_tasks())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)