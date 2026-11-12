"""
Seed script for NovaAI Chatbot
Creates a sample user and demonstration conversation threads.
"""

from app import app
from models import db, User, Conversation, Message, Feedback


def seed_database():
    with app.app_context():
        # Check if demo user already exists
        demo_user = User.query.filter_by(email='demo@nova.ai').first()
        if not demo_user:
            demo_user = User(
                name='Alex Mercer',
                email='demo@nova.ai'
            )
            demo_user.set_password('demo1234')
            db.session.add(demo_user)
            db.session.commit()
            print(f"Created demo user: {demo_user.email} / password: demo1234")

        # Check if conversations already exist
        if Conversation.query.filter_by(user_id=demo_user.id).count() == 0:
            conv = Conversation(
                user_id=demo_user.id,
                title='Python Batch Data Processor'
            )
            db.session.add(conv)
            db.session.flush()

            msg1 = Message(
                conversation_id=conv.id,
                role='user',
                content='Help me write a Python class to process data in batches with error recovery.'
            )
            db.session.add(msg1)

            code_sample = (
                "### 🚀 High-Performance Task Processor\n\n"
                "Here is a production-grade batch processor with exponential retry logic:\n\n"
                "```python\n"
                "from typing import List, Dict, Any\n"
                "import time\n\n"
                "class BatchProcessor:\n"
                "    def __init__(self, batch_size: int = 50):\n"
                "        self.batch_size = batch_size\n"
                "        \n"
                "    def run(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:\n"
                "        for i in range(0, len(records), self.batch_size):\n"
                "            chunk = records[i:i + self.batch_size]\n"
                "            self._process_chunk(chunk)\n"
                "        return {'status': 'completed', 'total': len(records)}\n"
                "```\n\n"
                "Let me know if you would like me to add logging or async workers!"
            )
            msg2 = Message(
                conversation_id=conv.id,
                role='assistant',
                content=code_sample
            )
            db.session.add(msg2)
            db.session.flush()

            fb = Feedback(
                message_id=msg2.id,
                user_id=demo_user.id,
                rating='up'
            )
            db.session.add(fb)
            db.session.commit()
            print("Sample conversation and messages populated.")


if __name__ == '__main__':
    seed_database()

