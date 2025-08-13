# task_monitor.py - Enhanced task monitoring
import asyncio
import socketio
from celery_app import celery_app
from celery.result import AsyncResult
import time

class TaskMonitor:
    def __init__(self, socketio_server):
        self.sio = socketio_server
        self.active_tasks = {}
        self.monitoring = False
    
    async def start_monitoring(self):
        """Start monitoring active tasks"""
        self.monitoring = True
        while self.monitoring:
            try:
                await self.check_task_updates()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                print(f"Error in task monitoring: {e}")
                await asyncio.sleep(5)
    
    async def check_task_updates(self):
        """Check for task status updates"""
        for task_id in list(self.active_tasks.keys()):
            try:
                result = AsyncResult(task_id, app=celery_app)
                current_status = result.status
                
                # Check if status changed
                if self.active_tasks[task_id]['status'] != current_status:
                    self.active_tasks[task_id]['status'] = current_status
                    
                    # Prepare update data
                    update_data = {
                        'task_id': task_id,
                        'status': current_status,
                        'message': self._get_status_message(result),
                        'result': result.result if result.ready() else None
                    }
                    
                    # Emit update to all connected clients
                    await self.sio.emit('task_update', update_data)
                    
                    # Remove completed tasks after some time
                    if current_status in ['SUCCESS', 'FAILURE']:
                        asyncio.create_task(self._cleanup_task(task_id, delay=30))
                        
            except Exception as e:
                print(f"Error checking task {task_id}: {e}")
    
    def add_task(self, task_id):
        """Add task to monitoring"""
        self.active_tasks[task_id] = {
            'status': 'PENDING',
            'added_at': time.time()
        }
    
    async def _cleanup_task(self, task_id, delay=30):
        """Remove task from monitoring after delay"""
        await asyncio.sleep(delay)
        self.active_tasks.pop(task_id, None)
    
    def _get_status_message(self, result):
        """Get appropriate message based on task status"""
        status = result.status
        if status == 'PENDING':
            return 'Task is waiting in queue'
        elif status == 'PROGRESS':
            if result.result and isinstance(result.result, dict):
                return result.result.get('status', 'Task in progress')
            return 'Task in progress'
        elif status == 'SUCCESS':
            return 'Task completed successfully'
        elif status == 'FAILURE':
            return f'Task failed: {result.result}'
        else:
            return f'Task status: {status}'