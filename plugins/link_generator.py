# (©)Codexbotz

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from asyncio import TimeoutError
import asyncio
from helper_func import encode, get_message_id, encode_link, decode_link
from config import *
from database.database import get_cloned_bot_by_username

async def get_bot_config(client):
    """Get bot configuration"""
    bot_data = await get_cloned_bot_by_username(client.username)
    
    if bot_data:
        return {
            'is_cloned': True,
            'admins': bot_data['admins'],
            'db_channel_id': bot_data['db_channel_id']
        }
    else:
        return {
            'is_cloned': False,
            'admins': ADMINS,
            'db_channel_id': CHANNEL_ID
        }

@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    """Generate batch link"""
    config = await get_bot_config(client)
    if message.from_user.id not in config['admins']:
        return
    
    # Get first message
    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from DB Channel (with Quotes) or send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}", quote=True)
            return
        
        f_channel_id, f_msg_id = await get_message_id(client, first_message)
        if f_channel_id and f_msg_id:
            # For cloned bots, use their DB channel
            if config['is_cloned'] and config['db_channel_id']:
                f_channel_id = config['db_channel_id']
            break
        else:
            await first_message.reply_text(
                "❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is not taken from DB Channel",
                quote=True
            )

    # Get second message
    while True:
        try:
            second_message = await client.ask(
                text="Forward the Last Message from DB Channel (with Quotes) or send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}", quote=True)
            return
        
        s_channel_id, s_msg_id = await get_message_id(client, second_message)
        if s_channel_id and s_msg_id:
            if config['is_cloned'] and config['db_channel_id']:
                s_channel_id = config['db_channel_id']
            
            if s_channel_id == f_channel_id:
                if s_msg_id < f_msg_id:
                    await second_message.reply_text(
                        "❌ Error\n\nThe last message ID must be greater than or equal to the first message ID.",
                        quote=True
                    )
                    continue
                break
            else:
                await second_message.reply_text(
                    "❌ Error\n\nThe second message must be from the same channel as the first message.",
                    quote=True
                )
        else:
            await second_message.reply_text(
                "❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is not taken from DB Channel",
                quote=True
            )

    # Generate link using encode_link with *43
    try:
        base64_string = await encode_link(f_msg_id=f_msg_id, s_msg_id=s_msg_id, channel_id=f_channel_id)
        link = f"https://t.me/{client.username}?start={base64_string}"
        print(f"Generated batch link: {link}")
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]
        ])
        await second_message.reply_text(
            f"<b>Here is your batch link</b>\n\n{link}",
            quote=True,
            reply_markup=reply_markup
        )
    except ValueError as e:
        await second_message.reply_text(f"❌ Error generating link: {str(e)}", quote=True)
    except Exception as e:
        await second_message.reply_text(f"❌ Unexpected error: {str(e)}", quote=True)


@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    """Generate single message link"""
    config = await get_bot_config(client)
    if message.from_user.id not in config['admins']:
        return
    
    while True:
        try:
            channel_message = await client.ask(
                text="Forward Message from the DB Channel (with Quotes)..\nor Send the DB Channel Post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        
        channel_id, msg_id = await get_message_id(client, channel_message)
        if channel_id and msg_id:
            # For cloned bots, use their DB channel
            if config['is_cloned'] and config['db_channel_id']:
                channel_id = config['db_channel_id']
            break
        else:
            await channel_message.reply("❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is not taken from DB Channel", quote=True)
            continue

    # Generate single message link using encode_link with *43
    base64_string = await encode_link(f_msg_id=msg_id, channel_id=channel_id)
    link = f"https://t.me/{client.username}?start={base64_string}"
    print(f"Generated single link: {link}")
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)

@Client.on_message(filters.private & filters.command("custom_batch"))
async def custom_batch(client: Client, message: Message):
    """Create custom batch from multiple messages"""
    config = await get_bot_config(client)
    if message.from_user.id not in config['admins']:
        return
    
    collected = []
    STOP_KEYBOARD = ReplyKeyboardMarkup([["STOP"]], resize_keyboard=True)

    await message.reply("Send all messages you want to include in batch.\n\nPress STOP when you're done.", reply_markup=STOP_KEYBOARD)

    db_channel_id = config['db_channel_id'] if config['is_cloned'] else client.db_channel.id

    while True:
        try:
            user_msg = await client.ask(
                chat_id=message.chat.id,
                text="Waiting for files/messages...\nPress STOP to finish.",
                timeout=60
            )
        except asyncio.TimeoutError:
            break

        if user_msg.text and user_msg.text.strip().upper() == "STOP":
            break

        try:
            sent = await user_msg.copy(db_channel_id, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"❌ Failed to store a message:\n<code>{e}</code>")
            continue

    await message.reply("✅ Batch collection complete.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        await message.reply("❌ No messages were added to batch.")
        return

    # Generate custom batch link using encode_link with *43
    base64_string = await encode_link(f_msg_id=collected[0], s_msg_id=collected[-1], channel_id=db_channel_id)
    link = f"https://t.me/{client.username}?start={base64_string}"
    print(f"Generated custom batch link: {link}")
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await message.reply(f"<b>Here is your custom batch link:</b>\n\n{link}", reply_markup=reply_markup)

@Client.on_message(filters.private & filters.command('nbatch'))
async def new_batch(client: Client, message: Message):
    """Generate new format batch link"""
    config = await get_bot_config(client)
    if message.from_user.id not in config['admins']:
        return
    
    # Get first message
    while True:
        try:
            first_message = await client.ask(
                text="Forward the First Message from DB Channel (with Quotes)..\n\nor Send the DB Channel Post Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        
        f_channel_id, f_msg_id = await get_message_id(client, first_message)
        if f_channel_id and f_msg_id:
            if config['is_cloned'] and config['db_channel_id']:
                f_channel_id = config['db_channel_id']
            break
        else:
            await first_message.reply("❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel", quote=True)
            continue

    # Get second message
    while True:
        try:
            second_message = await client.ask(
                text="Forward the Last Message from DB Channel (with Quotes)..\nor Send the DB Channel Post link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        
        s_channel_id, s_msg_id = await get_message_id(client, second_message)
        if s_channel_id and s_msg_id:
            if config['is_cloned'] and config['db_channel_id']:
                s_channel_id = config['db_channel_id']
            
            if s_channel_id == f_channel_id:
                break
            else:
                await second_message.reply("❌ Error\n\nThe second message must be from the same channel as the first message.", quote=True)
                continue
        else:
            await second_message.reply("❌ Error\n\nThis Forwarded Post is not from my DB Channel or this Link is taken from DB Channel", quote=True)
            continue

    # Use encode_link to generate the new format with *43
    base64_string = await encode_link(f_msg_id=f_msg_id, s_msg_id=s_msg_id, channel_id=f_channel_id)
    link = f"https://t.me/{client.username}?start={base64_string}"
    print(f"Generated new batch link: {link}")

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<b>Here is your new batch link</b>\n\n<code>{link}</code>", quote=True, reply_markup=reply_markup)
