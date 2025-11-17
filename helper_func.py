#(©)CodeFlix_Bots

import base64
import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, ADMINS
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, ChannelInvalid, PeerIdInvalid, ChatAdminRequired
from pyrogram.errors.exceptions.bad_request_400 import BadRequest, MessageIdsInvalid
from typing import Tuple, Union
from database.database import get_cloned_bot_by_username


async def is_subscribed(filter, client, update):
    """
    Check if user is subscribed to all required channels.
    Works for both main bot and cloned bots.
    """
    user_id = update.from_user.id
    
    # Check if it's a cloned bot
    bot_data = await get_cloned_bot_by_username(client.username)
    
    if bot_data:
        # Cloned bot - check its admins and force sub channels
        if user_id in bot_data['admins']:
            return True
        
        # Check all force sub channels for this cloned bot
        force_sub_channels = bot_data.get('force_sub_channels', [])
        if not force_sub_channels:
            return True
        
        for channel_data in force_sub_channels:
            try:
                member = await client.get_chat_member(chat_id=channel_data['channel_id'], user_id=user_id)
                if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                    return False
            except UserNotParticipant:
                return False
            except Exception as e:
                print(f"Error checking subscription for cloned bot {client.username}: {e}")
                return False
        return True
    else:
        # Main bot - use original logic
        if user_id in ADMINS:
            return True
        
        # Check all main bot force sub channels
        channels_to_check = []
        if FORCE_SUB_CHANNEL:
            channels_to_check.append(FORCE_SUB_CHANNEL)
        if FORCE_SUB_CHANNEL2:
            channels_to_check.append(FORCE_SUB_CHANNEL2)
        if FORCE_SUB_CHANNEL3:
            channels_to_check.append(FORCE_SUB_CHANNEL3)
        if FORCE_SUB_CHANNEL4:
            channels_to_check.append(FORCE_SUB_CHANNEL4)
        
        if not channels_to_check:
            return True
        
        for channel_id in channels_to_check:
            try:
                member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                    return False
            except UserNotParticipant:
                return False
            except Exception as e:
                print(f"Error checking subscription for main bot: {e}")
                return False
        
        return True

async def encode(string):
    """
    Simple base64 encoding (legacy support)
    """
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").strip("=")
    return base64_string

async def decode(base64_string):
    """
    Simple base64 decoding (legacy support)
    """
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string

async def encode_link(user_id: int = None, f_msg_id: int = None, s_msg_id: int = None, channel_id: int = None) -> str:
    """
    Encode a Telegram bot deep link for batch or HACKHEIST access with *43 multiplication.
    
    Args:
        user_id: User ID (required for HACKHEIST, optional for batch)
        f_msg_id: First message ID (required)
        s_msg_id: Second message ID (optional for batch, None for HACKHEIST or single message)
        channel_id: Channel ID (required)
        
    Returns:
        Base64 encoded string for bot deep link
        
    Examples:
        # HACKHEIST link (individual save)
        await encode_link(user_id=123456, f_msg_id=100, channel_id=-1001234567890)
        
        # Single message batch link
        await encode_link(f_msg_id=100, channel_id=-1001234567890)
        
        # Range batch link
        await encode_link(f_msg_id=100, s_msg_id=200, channel_id=-1001234567890)
    """
    if channel_id is None or f_msg_id is None:
        raise ValueError("channel_id and f_msg_id are required")
    
    if not all(isinstance(x, int) for x in [user_id, f_msg_id, s_msg_id, channel_id] if x is not None):
        raise ValueError("All IDs must be integers")
    
    # Apply *43 multiplication for obfuscation
    channel_id_encoded = channel_id * 43
    f_msg_id_encoded = f_msg_id * 43
    s_msg_id_encoded = s_msg_id * 43 if s_msg_id is not None else None
    
    # Create the string to encode
    if user_id is not None and s_msg_id is None:
        # HACKHEIST link: HACKHEIST-user_id-f_msg_id_encoded-channel_id_encoded
        raw_string = f"HACKHEIST-{user_id}-{f_msg_id_encoded}-{channel_id_encoded}"
    elif s_msg_id is not None:
        # Batch link for message range: get-channel_id_encoded-f_msg_id_encoded-s_msg_id_encoded
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}-{s_msg_id_encoded}"
    else:
        # Batch link for single message: get-channel_id_encoded-f_msg_id_encoded
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}"
    
    # Encode to base64
    string_bytes = raw_string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").rstrip("=")
    
    return f"{base64_string}"

async def decode_link(encoded_string: str) -> Tuple[str, Union[int, None], int, int, Union[int, None]]:
    """
    Decode a base64 string from a Telegram bot deep link, reversing *43 multiplication.
    
    Args:
        encoded_string: The base64 encoded string (without the Telegram URL prefix)
        
    Returns:
        Tuple of (link_type, user_id, f_msg_id, channel_id, s_msg_id)
        - link_type: "HACKHEIST" or "batch"
        - user_id: User ID (for HACKHEIST) or None (for batch)
        - f_msg_id: First message ID
        - channel_id: Channel ID
        - s_msg_id: Second message ID (None for single message or HACKHEIST)
        
    Examples:
        link_type, user_id, f_msg_id, channel_id, s_msg_id = await decode_link("base64string")
    """
    # Restore padding for base64
    encoded_string = encoded_string + "=" * (-len(encoded_string) % 4)
    
    # Decode base64
    try:
        string_bytes = base64.urlsafe_b64decode(encoded_string)
        decoded_string = string_bytes.decode("ascii")
    except (base64.binascii.Error, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid base64 encoded string: {e}")
    
    # Parse the decoded string
    parts = decoded_string.split("-")
    
    if decoded_string.startswith("HACKHEIST-"):
        # HACKHEIST link format: HACKHEIST-user_id-f_msg_id_encoded-channel_id_encoded
        if len(parts) not in [4, 5]:
            raise ValueError(f"Invalid HACKHEIST string structure: {decoded_string}")
        try:
            user_id = int(parts[1])
            f_msg_id = int(parts[2]) // 43
            
            # Handle negative channel IDs
            if len(parts) == 5 and parts[3] == "":
                # Negative channel_id: HACKHEIST-user_id-f_msg_id_encoded--channel_id_encoded
                channel_id = int(f"-{parts[4]}") // 43
            else:
                # Positive channel_id: HACKHEIST-user_id-f_msg_id_encoded-channel_id_encoded
                channel_id = int(parts[3]) // 43
            
            return "HACKHEIST", user_id, f_msg_id, channel_id, None
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid number format in HACKHEIST string: {e}")
    
    elif decoded_string.startswith("get-"):
        # Batch link formats:
        # Single: get-channel_id_encoded-f_msg_id_encoded
        # Range: get-channel_id_encoded-f_msg_id_encoded-s_msg_id_encoded
        if len(parts) not in [3, 4, 5]:
            raise ValueError(f"Invalid batch string structure: {decoded_string}")
        try:
            # Handle negative channel IDs
            if len(parts) == 5 and parts[1] == "":
                # Negative channel_id with range: get--channel_id_encoded-f_msg_id_encoded-s_msg_id_encoded
                channel_id = int(f"-{parts[2]}") // 43
                f_msg_id = int(parts[3]) // 43
                s_msg_id = int(parts[4]) // 43
            elif len(parts) == 4 and parts[1] != "":
                # Positive channel_id with range: get-channel_id_encoded-f_msg_id_encoded-s_msg_id_encoded
                channel_id = int(parts[1]) // 43
                f_msg_id = int(parts[2]) // 43
                s_msg_id = int(parts[3]) // 43
            elif len(parts) == 4 and parts[1] == "":
                # Negative channel_id, single message: get--channel_id_encoded-f_msg_id_encoded
                channel_id = int(f"-{parts[2]}") // 43
                f_msg_id = int(parts[3]) // 43
                s_msg_id = None
            elif len(parts) == 3:
                # Positive channel_id, single message: get-channel_id_encoded-f_msg_id_encoded
                channel_id = int(parts[1]) // 43
                f_msg_id = int(parts[2]) // 43
                s_msg_id = None
            else:
                raise ValueError(f"Invalid batch string structure: {decoded_string}")
            
            return "batch", None, f_msg_id, channel_id, s_msg_id
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid number format in batch string: {e}")
    
    else:
        raise ValueError(f"Invalid encoded string format: must start with 'HACKHEIST-' or 'get-', got: {decoded_string[:20]}")

async def get_messages(client, message_ids, channel_id):
    """
    Fetch messages from a specified channel by message IDs.
    
    Args:
        client: Pyrogram client
        message_ids: List of message IDs to fetch
        channel_id: Channel ID to fetch messages from
        
    Returns:
        List of fetched messages (may include None for inaccessible messages)
        
    Examples:
        messages = await get_messages(client, [100, 101, 102], -1001234567890)
    """
    messages = []
    total_messages = 0

    if not message_ids:
        print("No message IDs provided")
        return messages
    if not channel_id:
        print("No channel ID provided")
        return messages

    # Validate channel access
    try:
        await client.get_chat(channel_id)
        print(f"✅ Access confirmed for channel {channel_id}")
    except ChannelInvalid:
        print(f"❌ Invalid channel ID: {channel_id}")
        return messages
    except ChatAdminRequired:
        print(f"❌ Bot requires admin access to channel: {channel_id}")
        return messages
    except Exception as e:
        print(f"❌ Error accessing channel {channel_id}: {e}")
        return messages

    # Fetch messages in batches of 200
    while total_messages < len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(
                chat_id=channel_id,
                message_ids=temb_ids
            )
            # Filter out None values
            valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
            if valid_msgs:
                print(f"✅ Fetched {len(valid_msgs)}/{len(temb_ids)} messages for channel {channel_id}")
            else:
                print(f"⚠️ No valid messages found for IDs {temb_ids} in channel {channel_id}")
            messages.extend(valid_msgs)
        except FloodWait as e:
            print(f"⏳ FloodWait: Waiting {e.value} seconds for channel {channel_id}")
            await asyncio.sleep(e.value)
            try:
                msgs = await client.get_messages(
                    chat_id=channel_id,
                    message_ids=temb_ids
                )
                valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
                if valid_msgs:
                    print(f"✅ Fetched {len(valid_msgs)}/{len(temb_ids)} messages after FloodWait")
                messages.extend(valid_msgs)
            except Exception as e:
                print(f"❌ Error after FloodWait for IDs {temb_ids}: {e}")
        except MessageIdsInvalid:
            print(f"❌ Invalid message IDs: {temb_ids} in channel {channel_id}")
        except Exception as e:
            print(f"❌ Error fetching messages for IDs {temb_ids}: {e}")
        total_messages += len(temb_ids)

    if messages:
        print(f"✅ Successfully fetched {len(messages)}/{len(message_ids)} messages from channel {channel_id}")
    else:
        print(f"❌ No messages fetched for IDs {message_ids} in channel {channel_id}")
    return messages

async def get_message_id(client, message):
    """
    Extract channel ID and message ID from forwarded message or Telegram link.
    
    Args:
        client: Pyrogram client
        message: Message object containing forwarded message or link
        
    Returns:
        Tuple of (channel_id, message_id) or (None, 0) if extraction fails
        
    Supported formats:
        - Forwarded messages from channels
        - Private channel links: https://t.me/c/1234567890/123
        - Public channel links: https://t.me/channelname/123
    """
    if message.forward_from_chat:
        # Handle forwarded messages from channels
        return message.forward_from_chat.id, message.forward_from_message_id
    
    elif message.forward_from:
        # Forwarded from a user, invalid for this use case
        return None, 0
    
    elif message.text:
        # Handle both private and public channel links
        # Private: https://t.me/c/2493255368/45956
        # Public: https://t.me/username/45956
        pattern = r"https://t\.me/(?:c/)?([^/]+)/(\d+)"
        matches = re.match(pattern, message.text)
        if not matches:
            return None, 0
        
        channel_identifier = matches.group(1)  # Either channel ID (digits) or username
        msg_id = int(matches.group(2))
        
        try:
            if channel_identifier.isdigit():
                # Private channel (e.g., 2493255368)
                # Add -100 prefix for private channels
                channel_id = int(f"-100{channel_identifier}")
            else:
                # Public channel (e.g., username)
                chat = await client.get_chat(channel_identifier)
                channel_id = chat.id
            return channel_id, msg_id
        except Exception as e:
            print(f"Error extracting channel ID from link: {e}")
            return None, 0
    else:
        return None, 0

def get_readable_time(seconds: int) -> str:
    """
    Convert seconds to readable time format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string (e.g., "2h:30m:45s" or "1 days, 5h:30m:15s")
        
    Examples:
        get_readable_time(3661) -> "1h:1m:1s"
        get_readable_time(90061) -> "1 days, 1h:1m:1s"
    """
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

# Create subscribed filter for pyrogram
subscribed = filters.create(is_subscribed)
