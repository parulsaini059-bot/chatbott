import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, current_app, Response, stream_with_context
from flask_login import login_required, current_user
from models import db, Conversation, Message, Feedback
from services.ai_service import AIService

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/')
@login_required
def index():
    """Main chat application interface."""
    ai_service = AIService(current_app.config)
    provider_info = ai_service.get_active_provider_info()
    return render_template(
        'index.html',
        user=current_user,
        provider_info=provider_info
    )


@chat_bp.route('/api/chat/provider-info', methods=['GET'])
@login_required
def get_provider_info():
    """Get the active AI provider and model status."""
    ai_service = AIService(current_app.config)
    return jsonify(ai_service.get_active_provider_info())


@chat_bp.route('/api/chat/send', methods=['POST'])
@login_required
def send_message():
    """
    Send user message, persist to database, query real LLM service, and return response.
    """
    data = request.get_json() or {}
    user_text = data.get('message', '').strip()
    conv_id = data.get('conversation_id')

    if not user_text:
        return jsonify({'error': 'Message content cannot be empty.'}), 400

    # 1. Resolve or create Conversation
    is_new_conversation = False
    conv = None
    if conv_id:
        conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()

    if not conv:
        title = user_text.split('\n')[0][:40].strip()
        if len(user_text) > 40:
            title += "..."
        conv = Conversation(user_id=current_user.id, title=title or "New Chat")
        db.session.add(conv)
        db.session.flush()
        is_new_conversation = True

    # 2. Persist User Message
    user_msg = Message(
        conversation_id=conv.id,
        role='user',
        content=user_text
    )
    db.session.add(user_msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # 3. Build Conversation Context with memory (most recent 30 messages in chronological order)
    recent_messages = (
        Message.query
        .filter_by(conversation_id=conv.id)
        .order_by(Message.created_at.desc())
        .limit(30)
        .all()
    )
    recent_messages.reverse()
    context = [{'role': m.role, 'content': m.content} for m in recent_messages]

    # 4. Generate AI Response via real LLM
    ai_service = AIService(current_app.config)
    req_provider = data.get('provider')
    req_model = data.get('model')
    if req_provider:
        ai_service.provider = req_provider.lower()
    if req_model:
        if ai_service.provider == 'gemini':
            ai_service.gemini_model = req_model
        elif ai_service.provider == 'openai':
            ai_service.openai_model = req_model
        elif ai_service.provider == 'groq':
            ai_service.groq_model = req_model

    ai_result = ai_service.generate_response(context)

    # 5. Persist Assistant Message
    bot_msg = Message(
        conversation_id=conv.id,
        role='assistant',
        content=ai_result['content']
    )
    db.session.add(bot_msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'success': True,
        'is_new_conversation': is_new_conversation,
        'conversation': {
            'id': conv.id,
            'title': conv.title,
            'updated_at': conv.updated_at.isoformat()
        },
        'user_message': user_msg.to_dict(current_user_id=current_user.id),
        'bot_message': {
            **bot_msg.to_dict(current_user_id=current_user.id),
            'provider': ai_result.get('provider', ai_service.provider),
            'model': ai_result.get('model', ''),
            'is_error': ai_result.get('is_error', False)
        }
    })


@chat_bp.route('/api/chat/send-stream', methods=['POST'])
@login_required
def send_message_stream():
    """
    Streaming chat endpoint via Server-Sent Events (SSE).
    Tokens stream in real time directly from Google Gemini, OpenAI, or Groq.
    """
    data = request.get_json() or {}
    user_text = data.get('message', '').strip()
    conv_id = data.get('conversation_id')

    if not user_text:
        return jsonify({'error': 'Message cannot be empty.'}), 400

    is_new = False
    conv = None
    if conv_id:
        conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()

    if not conv:
        title = user_text.split('\n')[0][:40].strip()
        if len(user_text) > 40:
            title += "..."
        conv = Conversation(user_id=current_user.id, title=title or "New Chat")
        db.session.add(conv)
        db.session.flush()
        is_new = True

    # Save User message
    user_msg = Message(
        conversation_id=conv.id,
        role='user',
        content=user_text
    )
    db.session.add(user_msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # Build conversation memory
    recent_messages = (
        Message.query
        .filter_by(conversation_id=conv.id)
        .order_by(Message.created_at.desc())
        .limit(30)
        .all()
    )
    recent_messages.reverse()
    context = [{'role': m.role, 'content': m.content} for m in recent_messages]

    ai_service = AIService(current_app.config)
    req_provider = data.get('provider')
    req_model = data.get('model')
    if req_provider:
        ai_service.provider = req_provider.lower()
    if req_model:
        if ai_service.provider == 'gemini':
            ai_service.gemini_model = req_model
        elif ai_service.provider == 'openai':
            ai_service.openai_model = req_model
        elif ai_service.provider == 'groq':
            ai_service.groq_model = req_model

    conv_id_val = conv.id
    conv_title_val = conv.title
    user_msg_dict = user_msg.to_dict(current_user_id=current_user.id)

    def stream_generator():
        # Send initial metadata
        yield f"data: {json.dumps({'meta': True, 'conversation_id': conv_id_val, 'conversation_title': conv_title_val, 'is_new': is_new, 'user_message': user_msg_dict})}\n\n"

        full_content = []
        for chunk_str in ai_service.stream_response(context):
            try:
                chunk = json.loads(chunk_str.strip())
                if 'delta' in chunk:
                    full_content.append(chunk['delta'])
                yield f"data: {json.dumps(chunk)}\n\n"
            except Exception:
                continue

        # Save assistant message to database
        complete_text = "".join(full_content).strip()
        if complete_text:
            try:
                bot_msg = Message(
                    conversation_id=conv_id_val,
                    role='assistant',
                    content=complete_text
                )
                db.session.add(bot_msg)
                c = db.session.get(Conversation, conv_id_val)
                if c:
                    c.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                yield f"data: {json.dumps({'saved': True, 'message_id': bot_msg.id})}\n\n"
            except Exception as e:
                db.session.rollback()

    return Response(stream_with_context(stream_generator()), mimetype='text/event-stream')


@chat_bp.route('/api/chat/regenerate', methods=['POST'])
@login_required
def regenerate_response():
    """
    Regenerate the latest assistant response using full conversation memory.
    """
    data = request.get_json() or {}
    conv_id = data.get('conversation_id')

    if not conv_id:
        return jsonify({'error': 'Conversation ID is required.'}), 400

    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({'error': 'Conversation not found.'}), 404

    # Fetch last message
    last_msg = (
        Message.query
        .filter_by(conversation_id=conv.id)
        .order_by(Message.created_at.desc())
        .first()
    )

    if not last_msg:
        return jsonify({'error': 'No messages to regenerate.'}), 400

    # If the last message was assistant, remove it before regenerating
    if last_msg.role == 'assistant':
        db.session.delete(last_msg)
        db.session.commit()

    # Re-fetch context (up to 30 recent messages)
    recent_messages = (
        Message.query
        .filter_by(conversation_id=conv.id)
        .order_by(Message.created_at.desc())
        .limit(30)
        .all()
    )
    recent_messages.reverse()

    if not recent_messages:
        return jsonify({'error': 'No previous user messages found.'}), 400

    context = [{'role': m.role, 'content': m.content} for m in recent_messages]

    # Generate new AI Response
    ai_service = AIService(current_app.config)
    ai_result = ai_service.generate_response(context)

    # Persist New Assistant Message
    new_bot_msg = Message(
        conversation_id=conv.id,
        role='assistant',
        content=ai_result['content']
    )
    db.session.add(new_bot_msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'success': True,
        'bot_message': {
            **new_bot_msg.to_dict(current_user_id=current_user.id),
            'provider': ai_result.get('provider', ai_service.provider),
            'model': ai_result.get('model', ''),
            'is_error': ai_result.get('is_error', False)
        }
    })


@chat_bp.route('/api/messages/<int:message_id>/feedback', methods=['POST'])
@login_required
def message_feedback(message_id):
    """
    Record user thumbs up / thumbs down feedback on a message.
    """
    data = request.get_json() or {}
    rating = data.get('rating')

    if rating not in ('up', 'down', None):
        return jsonify({'error': 'Rating must be "up", "down", or null.'}), 400

    msg = (
        Message.query
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Message.id == message_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not msg:
        return jsonify({'error': 'Message not found or access denied.'}), 404

    existing_feedback = Feedback.query.filter_by(
        message_id=message_id,
        user_id=current_user.id
    ).first()

    if rating is None:
        if existing_feedback:
            db.session.delete(existing_feedback)
            db.session.commit()
        return jsonify({'success': True, 'rating': None})

    if existing_feedback:
        existing_feedback.rating = rating
    else:
        new_feedback = Feedback(
            message_id=message_id,
            user_id=current_user.id,
            rating=rating
        )
        db.session.add(new_feedback)

    db.session.commit()
    return jsonify({'success': True, 'rating': rating})
