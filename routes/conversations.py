from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from models import db, Conversation, Message

conversations_bp = Blueprint('conversations', __name__, url_prefix='/api/conversations')


def categorize_date(dt: datetime) -> str:
    """Categorize a UTC datetime into Today, Yesterday, Previous 7 Days, or Older."""
    if not dt:
        return 'Older'
    
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    yesterday_start = today_start - timedelta(days=1)
    seven_days_ago = today_start - timedelta(days=7)

    if dt >= today_start:
        return 'Today'
    elif dt >= yesterday_start:
        return 'Yesterday'
    elif dt >= seven_days_ago:
        return 'Previous 7 Days'
    else:
        return 'Older'


@conversations_bp.route('', methods=['GET'])
@login_required
def get_conversations():
    """Retrieve all conversations for the authenticated user, ordered by recent activity."""
    try:
        convs = (
            Conversation.query
            .filter_by(user_id=current_user.id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

        # Prepare grouped structure
        grouped = {
            'Today': [],
            'Yesterday': [],
            'Previous 7 Days': [],
            'Older': []
        }
        all_list = []

        for conv in convs:
            item = conv.to_dict()
            category = categorize_date(conv.updated_at)
            item['group'] = category
            grouped[category].append(item)
            all_list.append(item)

        return jsonify({
            'success': True,
            'conversations': all_list,
            'grouped': grouped
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('', methods=['POST'])
@login_required
def create_conversation():
    """Create a new conversation thread."""
    data = request.get_json() or {}
    title = data.get('title', 'New Chat').strip()
    if not title:
        title = 'New Chat'

    try:
        conv = Conversation(
            user_id=current_user.id,
            title=title[:255]
        )
        db.session.add(conv)
        db.session.commit()
        return jsonify({
            'success': True,
            'conversation': conv.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/<int:conv_id>', methods=['GET'])
@login_required
def get_conversation_details(conv_id):
    """Retrieve a single conversation and its full message history."""
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({'error': 'Conversation not found or access denied.'}), 404

    # Fetch messages with current user's feedback
    messages_data = [msg.to_dict(current_user_id=current_user.id) for msg in conv.messages]

    return jsonify({
        'success': True,
        'conversation': {
            'id': conv.id,
            'title': conv.title,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
            'messages': messages_data
        }
    })


@conversations_bp.route('/<int:conv_id>', methods=['PUT'])
@login_required
def rename_conversation(conv_id):
    """Rename an existing conversation."""
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({'error': 'Conversation not found or access denied.'}), 404

    data = request.get_json() or {}
    new_title = data.get('title', '').strip()
    if not new_title:
        return jsonify({'error': 'Title cannot be blank.'}), 400

    conv.title = new_title[:255]
    conv.updated_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'conversation': conv.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/<int:conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    """Delete a conversation and all attached messages."""
    conv = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({'error': 'Conversation not found or access denied.'}), 404

    try:
        db.session.delete(conv)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Conversation deleted.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/clear-all', methods=['DELETE'])
@login_required
def clear_all_conversations():
    """Delete all conversations belonging to the current user."""
    try:
        Conversation.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'All conversations cleared.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/search', methods=['GET'])
@login_required
def search_conversations():
    """Search conversations by title or message content."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'conversations': []})

    # Search conversations by title OR messages containing query
    matching_conv_ids = (
        db.session.query(Message.conversation_id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == current_user.id)
        .filter(Message.content.ilike(f'%{query}%'))
        .distinct()
        .all()
    )
    ids_from_messages = [cid[0] for cid in matching_conv_ids]

    convs = (
        Conversation.query
        .filter_by(user_id=current_user.id)
        .filter(
            or_(
                Conversation.title.ilike(f'%{query}%'),
                Conversation.id.in_(ids_from_messages)
            )
        )
        .order_by(Conversation.updated_at.desc())
        .limit(25)
        .all()
    )

    results = []
    for conv in convs:
        results.append({
            'id': conv.id,
            'title': conv.title,
            'updated_at': conv.updated_at.isoformat(),
            'message_count': len(conv.messages)
        })

    return jsonify({
        'success': True,
        'query': query,
        'conversations': results
    })

