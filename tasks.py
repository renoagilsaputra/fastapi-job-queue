# tasks.py - Celery Tasks
import time
import random
from celery import current_task
from celery_app import celery_app
import asyncio
import socketio

# Socket.IO client untuk mengirim updates
sio_client = None

async def init_socketio_client():
    global sio_client
    if sio_client is None:
        sio_client = socketio.AsyncClient()
        try:
            await sio_client.connect('http://localhost:8000')
        except:
            pass

async def send_task_update(task_id, status, message, result=None):
    """Send task update via Socket.IO"""
    try:
        if sio_client and sio_client.connected:
            await sio_client.emit('task_update', {
                'task_id': task_id,
                'status': status,
                'message': message,
                'result': result
            })
    except Exception as e:
        print(f"Error sending socket update: {e}")

@celery_app.task(bind=True)
def process_long_task(self, task_name, duration):
    """
    Long-running task that updates progress
    """
    try:
        # Update task status to PROGRESS
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': duration, 'status': f'Processing {task_name}...'}
        )
        
        # Simulate long-running work with progress updates
        for i in range(duration):
            time.sleep(1)  # Simulate work
            
            # Update progress
            progress = int((i + 1) / duration * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': duration,
                    'status': f'Processing {task_name}... ({progress}%)'
                }
            )
        
        # Complete the task
        result = {
            'task_name': task_name,
            'duration': duration,
            'completed_at': time.time(),
            'message': f'Task "{task_name}" completed successfully!'
        }
        
        return result
        
    except Exception as exc:
        # Handle task failure
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'task_name': task_name}
        )
        raise exc

@celery_app.task(bind=True)
def send_email_task(self, email, subject, body):
    """
    Email sending task (mock implementation)
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Preparing email...'}
        )
        
        # Simulate email preparation
        time.sleep(2)
        
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Connecting to email server...'}
        )
        
        # Simulate connection
        time.sleep(1)
        
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Sending email...'}
        )
        
        # Simulate sending
        time.sleep(2)
        
        # Mock success/failure
        if random.random() > 0.2:  # 80% success rate
            result = {
                'email': email,
                'subject': subject,
                'status': 'sent',
                'message': f'Email successfully sent to {email}',
                'sent_at': time.time()
            }
            return result
        else:
            raise Exception("Failed to send email - SMTP error")
            
    except Exception as exc:
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'email': email}
        )
        raise exc

# Additional utility tasks
@celery_app.task
def cleanup_old_tasks():
    """Periodic task to cleanup old task results"""
    # Implementation untuk cleanup
    pass

@celery_app.task(bind=True)
def process_file_task(self, file_path, operation):
    """File processing task"""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Reading file...'})
        time.sleep(1)
        
        self.update_state(state='PROGRESS', meta={'status': f'Performing {operation}...'})
        time.sleep(3)
        
        self.update_state(state='PROGRESS', meta={'status': 'Saving results...'})
        time.sleep(1)
        
        return {'file_path': file_path, 'operation': operation, 'status': 'completed'}
    except Exception as exc:
        self.update_state(state='FAILURE', meta={'error': str(exc)})
        raise exc