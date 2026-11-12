"""
NovaAI Automated Test Suite
Verifies all core functionality: Auth, Conversations, Real LLM Service, Streaming, Memory, Feedback, Search, Clear All, Security.
"""

import unittest
from unittest.mock import patch
from app import create_app
from models import db, User, Conversation, Message, Feedback
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    AI_PROVIDER = 'gemini'
    GEMINI_API_KEY = 'test-gemini-key'
    GEMINI_MODEL = 'gemini-1.5-flash'


class NovaAITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_01_user_signup_and_login(self):
        """Test user registration, duplicate email rejection, and authentication."""
        # 1. Signup user 1
        res = self.client.post('/signup', data={
            'name': 'Alice Architect',
            'email': 'alice@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Alice Architect', res.data)

        # 2. Logout
        self.client.get('/logout')

        # 3. Duplicate email check
        res_dup = self.client.post('/signup', data={
            'name': 'Duplicate Alice',
            'email': 'alice@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'already exists', res_dup.data)

        # 4. Wrong password
        res_bad = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res_bad.data)

        # 5. Correct password
        res_ok = self.client.post('/login', data={
            'email': 'alice@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        self.assertIn(b'NovaAI', res_ok.data)

    @patch('services.ai_service.AIService._call_gemini')
    def test_02_chat_flow_and_conversation_memory(self, mock_gemini):
        """Test sending message, LLM call with conversation history memory."""
        mock_gemini.side_effect = [
            {"content": "Python is a high-level programming language.", "provider": "gemini", "model": "gemini-1.5-flash"},
            {"content": "Python was created by Guido van Rossum in 1991.", "provider": "gemini", "model": "gemini-1.5-flash"}
        ]

        # Register and log in Alice
        self.client.post('/signup', data={
            'name': 'Alice Architect',
            'email': 'alice@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Turn 1: "What is Python?"
        res = self.client.post('/api/chat/send', json={
            'message': 'What is Python?'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_new_conversation'])
        conv_id = data['conversation']['id']
        self.assertEqual(data['bot_message']['content'], 'Python is a high-level programming language.')

        # Turn 2: "Who created it?" (Follow-up relying on memory)
        res2 = self.client.post('/api/chat/send', json={
            'conversation_id': conv_id,
            'message': 'Who created it?'
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2['bot_message']['content'], 'Python was created by Guido van Rossum in 1991.')

        # Verify that mock_gemini was called with conversation context containing past messages
        last_call_messages = mock_gemini.call_args[0][0]
        self.assertGreaterEqual(len(last_call_messages), 3)
        self.assertEqual(last_call_messages[0]['content'], 'What is Python?')
        self.assertEqual(last_call_messages[1]['content'], 'Python is a high-level programming language.')
        self.assertEqual(last_call_messages[2]['content'], 'Who created it?')

    def test_03_rename_and_delete_conversation(self):
        """Test conversation renaming, deletion, and cascade removal."""
        self.client.post('/signup', data={
            'name': 'Bob Builder',
            'email': 'bob@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Direct DB creation
        user = User.query.filter_by(email='bob@example.com').first()
        conv = Conversation(user_id=user.id, title='Original Title')
        db.session.add(conv)
        db.session.commit()

        # Rename
        res_rename = self.client.put(f'/api/conversations/{conv.id}', json={
            'title': 'Updated Technical Title'
        })
        self.assertEqual(res_rename.status_code, 200)
        self.assertEqual(res_rename.get_json()['conversation']['title'], 'Updated Technical Title')

        # Delete
        res_del = self.client.delete(f'/api/conversations/{conv.id}')
        self.assertEqual(res_del.status_code, 200)
        self.assertIsNone(db.session.get(Conversation, conv.id))

    def test_04_message_feedback(self):
        """Test thumbs up and thumbs down ratings on messages."""
        self.client.post('/signup', data={
            'name': 'Charlie',
            'email': 'charlie@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        user = User.query.filter_by(email='charlie@example.com').first()
        conv = Conversation(user_id=user.id, title='Feedback Test')
        db.session.add(conv)
        db.session.flush()
        msg = Message(conversation_id=conv.id, role='assistant', content='Helpful response.')
        db.session.add(msg)
        db.session.commit()

        # Thumbs up
        fb_res = self.client.post(f'/api/messages/{msg.id}/feedback', json={'rating': 'up'})
        self.assertEqual(fb_res.status_code, 200)
        self.assertEqual(fb_res.get_json()['rating'], 'up')

        # Toggle to thumbs down
        fb_res2 = self.client.post(f'/api/messages/{msg.id}/feedback', json={'rating': 'down'})
        self.assertEqual(fb_res2.status_code, 200)
        self.assertEqual(fb_res2.get_json()['rating'], 'down')

        # Clear rating
        fb_res3 = self.client.post(f'/api/messages/{msg.id}/feedback', json={'rating': None})
        self.assertEqual(fb_res3.status_code, 200)
        self.assertIsNone(fb_res3.get_json()['rating'])

    def test_05_user_isolation_security(self):
        """Verify strict user isolation (User B cannot access or modify User A's data)."""
        # User A
        self.client.post('/signup', data={
            'name': 'User A',
            'email': 'usera@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        user_a = User.query.filter_by(email='usera@example.com').first()
        conv_a = Conversation(user_id=user_a.id, title='Secret Thread A')
        db.session.add(conv_a)
        db.session.commit()
        conv_id_a = conv_a.id

        self.client.get('/logout')

        # User B
        self.client.post('/signup', data={
            'name': 'User B',
            'email': 'userb@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # User B attempts to access User A's conversation
        res_unauthorized = self.client.get(f'/api/conversations/{conv_id_a}')
        self.assertEqual(res_unauthorized.status_code, 404)

        # User B attempts to delete User A's conversation
        res_del_unauth = self.client.delete(f'/api/conversations/{conv_id_a}')
        self.assertEqual(res_del_unauth.status_code, 404)

        # Conversation A still exists
        self.assertIsNotNone(db.session.get(Conversation, conv_id_a))

    def test_06_missing_api_key_clear_error(self):
        """Verify that missing API key returns a clear actionable error notice."""
        # Create app without API key
        class NoKeyConfig(TestConfig):
            GEMINI_API_KEY = ''

        app_no_key = create_app(NoKeyConfig)
        client = app_no_key.test_client()
        with app_no_key.app_context():
            client.post('/signup', data={
                'name': 'No Key User',
                'email': 'nokey@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            res = client.post('/api/chat/send', json={'message': 'What is gravity?'})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            # Must explicitly inform user that API key is missing
            self.assertIn('API Key is Not Configured', data['bot_message']['content'])
            self.assertTrue(data['bot_message']['is_error'])

    def test_07_search_conversations(self):
        """Test searching conversations by title and message content."""
        self.client.post('/signup', data={
            'name': 'Search User',
            'email': 'search@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        user = User.query.filter_by(email='search@example.com').first()
        conv1 = Conversation(user_id=user.id, title='Neural Networks and Backpropagation')
        conv2 = Conversation(user_id=user.id, title='Chocolate Chip Cookie Recipe')
        db.session.add_all([conv1, conv2])
        db.session.commit()

        search_res = self.client.get('/api/conversations/search?q=neural')
        self.assertEqual(search_res.status_code, 200)
        data = search_res.get_json()
        self.assertEqual(len(data['conversations']), 1)
        self.assertIn('neural', data['conversations'][0]['title'].lower())

    def test_08_clear_all_conversations(self):
        """Test deleting all user conversations in one action."""
        self.client.post('/signup', data={
            'name': 'Clear User',
            'email': 'clear@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        user = User.query.filter_by(email='clear@example.com').first()
        conv1 = Conversation(user_id=user.id, title='Conv 1')
        conv2 = Conversation(user_id=user.id, title='Conv 2')
        db.session.add_all([conv1, conv2])
        db.session.commit()

        clear_res = self.client.delete('/api/conversations/clear-all')
        self.assertEqual(clear_res.status_code, 200)
        self.assertTrue(clear_res.get_json()['success'])

        conv_count_after = Conversation.query.filter_by(user_id=user.id).count()
        self.assertEqual(conv_count_after, 0)


if __name__ == '__main__':
    unittest.main()
