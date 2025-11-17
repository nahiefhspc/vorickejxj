import pymongo
import os
from config import DB_URI, DB_NAME
import time
import uuid

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]
user_data = database['users']
special_messages = database['special_messages']
scheduled_broadcasts = database['scheduled_broadcasts']
cloned_bots = database['cloned_bots']

# User functions
async def present_user(user_id: int):
    found = user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})
    return

async def full_userbase():
    user_docs = user_data.find()
    user_ids = []
    for doc in user_docs:
        user_ids.append(doc['_id'])
    return user_ids

async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})
    return

# Special messages functions
async def add_special_message(msg_id: int, bot_id: str):
    """Add a message ID to the special messages collection for a specific bot."""
    special_messages.update_one(
        {'_id': f"{bot_id}_special_msg_ids"},
        {'$addToSet': {'msg_ids': msg_id}},
        upsert=True
    )
    return

async def remove_special_message(msg_id: int, bot_id: str):
    """Remove a message ID from the special messages collection for a specific bot."""
    special_messages.update_one(
        {'_id': f"{bot_id}_special_msg_ids"},
        {'$pull': {'msg_ids': msg_id}}
    )
    return

async def get_special_messages(bot_id: str):
    """Retrieve all special message IDs for a specific bot."""
    doc = special_messages.find_one({'_id': f"{bot_id}_special_msg_ids"})
    return doc['msg_ids'] if doc and 'msg_ids' in doc else []

async def get_all_special_messages():
    """Retrieve all special message documents (for admin oversight)."""
    return list(special_messages.find())

# Scheduled broadcast functions
async def add_scheduled_broadcast(admin_chat_id: int, chat_id: int, reply_msg_id: int, total_time: int, interval: int, delete_after: int, start_delay: int = 0, bot_id: str = None):
    """Add a scheduled broadcast to the database with bot_id."""
    schedule_id = str(uuid.uuid4())
    schedule_data = {
        '_id': schedule_id,
        'admin_chat_id': admin_chat_id,
        'chat_id': chat_id,
        'reply_msg_id': reply_msg_id,
        'total_time': total_time,
        'interval': interval,
        'delete_after': delete_after,
        'start_delay': start_delay,
        'start_time': time.time(),
        'active': True,
        'bot_id': bot_id
    }
    scheduled_broadcasts.insert_one(schedule_data)
    return schedule_id

async def get_active_scheduled_broadcasts(bot_id: str = None):
    """Get all active scheduled broadcasts for a specific bot_id (or all if bot_id is None)."""
    query = {'active': True}
    if bot_id:
        query['bot_id'] = bot_id
    return list(scheduled_broadcasts.find(query))

async def deactivate_scheduled_broadcast(schedule_id: str):
    """Deactivate a specific scheduled broadcast."""
    scheduled_broadcasts.update_one(
        {'_id': schedule_id, 'active': True},
        {'$set': {'active': False}}
    )
    return

async def delete_scheduled_broadcast(schedule_id: str):
    """Delete a specific scheduled broadcast."""
    scheduled_broadcasts.delete_one({'_id': schedule_id})
    return

async def get_schedule_by_id(schedule_id: str):
    """Get a specific schedule by ID."""
    return scheduled_broadcasts.find_one({'_id': schedule_id})

async def update_schedule_start_time(schedule_id: str, start_time: float, start_delay: int = None):
    """Update the start_time and optionally start_delay for a schedule."""
    update_data = {'start_time': start_time}
    if start_delay is not None:
        update_data['start_delay'] = start_delay
    scheduled_broadcasts.update_one(
        {'_id': schedule_id},
        {'$set': update_data}
    )
    return

# Cloned Bots Functions
async def add_cloned_bot(bot_token: str, owner_id: int, bot_username: str, default_config: dict):
    """Add a new cloned bot with default configuration from main bot"""
    bot_data = {
        'bot_token': bot_token,
        'bot_username': bot_username,
        'owner_id': owner_id,
        'db_channel_id': None,
        'force_sub_channels': [],
        'start_msg': default_config.get('start_msg', "Hello {mention}!\n\nI can store and share files via special links."),
        'force_sub_msg': default_config.get('force_sub_msg', "Please join the required channels to access the bot."),
        'admins': [owner_id],
        'auto_delete_time': default_config.get('auto_delete_time', 14400),
        'individual_delete_time': default_config.get('individual_delete_time', 259200),
        'custom_caption': default_config.get('custom_caption', None),
        'protect_content': default_config.get('protect_content', True),
        'disable_channel_button': default_config.get('disable_channel_button', False),
        'created_at': time.time()
    }
    result = cloned_bots.insert_one(bot_data)
    return str(result.inserted_id)

async def get_cloned_bot(bot_token: str):
    """Get cloned bot by token"""
    return cloned_bots.find_one({'bot_token': bot_token})

async def get_cloned_bot_by_username(bot_username: str):
    """Get cloned bot by username"""
    return cloned_bots.find_one({'bot_username': bot_username})

async def get_all_cloned_bots():
    """Get all cloned bots"""
    return list(cloned_bots.find())

async def update_cloned_bot(bot_token: str, update_data: dict):
    """Update cloned bot configuration"""
    cloned_bots.update_one(
        {'bot_token': bot_token},
        {'$set': update_data}
    )
    return

async def delete_cloned_bot(bot_token: str):
    """Delete a cloned bot"""
    cloned_bots.delete_one({'bot_token': bot_token})
    return

async def add_force_sub_channel(bot_token: str, channel_id: int, invite_link: str):
    """Add a force sub channel to cloned bot"""
    cloned_bots.update_one(
        {'bot_token': bot_token},
        {'$addToSet': {'force_sub_channels': {'channel_id': channel_id, 'invite_link': invite_link}}}
    )
    return

async def remove_force_sub_channel(bot_token: str, channel_id: int):
    """Remove a force sub channel from cloned bot"""
    cloned_bots.update_one(
        {'bot_token': bot_token},
        {'$pull': {'force_sub_channels': {'channel_id': channel_id}}}
    )
    return

async def add_bot_admin(bot_token: str, admin_id: int):
    """Add an admin to cloned bot"""
    cloned_bots.update_one(
        {'bot_token': bot_token},
        {'$addToSet': {'admins': admin_id}}
    )
    return

async def remove_bot_admin(bot_token: str, admin_id: int):
    """Remove an admin from cloned bot"""
    cloned_bots.update_one(
        {'bot_token': bot_token},
        {'$pull': {'admins': admin_id}}
    )
    return
