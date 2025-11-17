#(©)Codexbotz

import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from config import ADMINS, CHANNEL_ID, DISABLE_CHANNEL_BUTTON
from helper_func import encode_link
from database.database import get_cloned_bot_by_username

async def get_bot_config(client):
    """Get bot configuration"""
    bot_data = await get_cloned_bot_by_username(client.username)
    
    if bot_data:
        return {
            'is_cloned': True,
            'admins': bot_data['admins'],
            'db_channel_id': bot_data['db_channel_id'],
            'disable_channel_button': bot_data['disable_channel_button']
        }
    else:
        return {
            'is_cloned': False,
            'admins': ADMINS,
            'db_channel_id': CHANNEL_ID,
            'disable_channel_button': DISABLE_CHANNEL_BUTTON
        }

@Client.on_message(filters.private & ~filters.command(['start','users','broadcast','batch','genlink','stats', 'add_random_message', 'remove_random_message', 'broadcast_add', 'broadcast_remove', 'resume', 'settings', 'add_bot', 'list_bots', 'remove_bot', 'custom_batch', 'nbatch', 'list_random_messages']))
async def channel_post(client: Client, message: Message):
    """Auto generate link when admin sends any media to bot"""
    config = await get_bot_config(client)
    
    # Check if user is admin
    if message.from_user.id not in config['admins']:
        return
    
    reply_text = await message.reply_text("Please Wait...!", quote=True)
    
    # Get DB channel ID
    db_channel_id = config['db_channel_id'] if config['is_cloned'] else client.db_channel.id
    
    if not db_channel_id:
        await reply_text.edit_text("❌ DB Channel not configured! Use /settings to set DB Channel.")
        return
    
    try:
        post_message = await message.copy(chat_id=db_channel_id, disable_notification=True)
    except FloodWait as e:
        await asyncio.sleep(e.x)
        post_message = await message.copy(chat_id=db_channel_id, disable_notification=True)
    except Exception as e:
        print(e)
        await reply_text.edit_text("Something went Wrong..!")
        return
    
    # Generate link using encode_link with *43
    base64_string = await encode_link(f_msg_id=post_message.id, channel_id=db_channel_id)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])

    await reply_text.edit(f"<b>Here is your link</b>\n\n<code>{link}</code>", reply_markup=reply_markup, disable_web_page_preview=True)

    if not config['disable_channel_button']:
        try:
            await post_message.edit_reply_markup(reply_markup)
        except:
            pass

@Client.on_message(filters.channel & filters.incoming)
async def new_post(client: Client, message: Message):
    """Auto add share button to channel posts"""
    config = await get_bot_config(client)
    
    # Check if message is from configured DB channel
    db_channel_id = config['db_channel_id'] if config['is_cloned'] else client.db_channel.id
    
    if not db_channel_id:
        return
    
    if message.chat.id != db_channel_id:
        return

    if config['disable_channel_button']:
        return

    # Generate link
    base64_string = await encode_link(f_msg_id=message.id, channel_id=db_channel_id)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    
    try:
        await message.edit_reply_markup(reply_markup)
    except Exception as e:
        print(e)
        pass
