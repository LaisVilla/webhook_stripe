from datetime import datetime
from app import firebase_admin


class Event:
    def __init__(self, title, description, start_time, end_time, user_id, event_id=None):
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.user_id = user_id
        self.event_id = event_id

    @staticmethod
    def from_dict(source):
        event = Event(
            title=source.get('title'),
            description=source.get('description'),
            start_time=source.get('start_time'),
            end_time=source.get('end_time'),
            user_id=source.get('user_id'),
            event_id=source.get('event_id')
        )
        return event

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'user_id': self.user_id,
            'event_id': self.event_id
        }

class Task:
    def __init__(self, title, description, due_date, status, priority, user_id, task_id=None):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.status = status
        self.priority = priority
        self.user_id = user_id
        self.task_id = task_id
        self.created_at = datetime.utcnow().isoformat()

    @staticmethod
    def from_dict(source):
        task = Task(
            title=source.get('title'),
            description=source.get('description'),
            due_date=source.get('due_date'),
            status=source.get('status'),
            priority=source.get('priority'),
            user_id=source.get('user_id'),
            task_id=source.get('task_id')
        )
        return task

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'created_at': self.created_at
        }