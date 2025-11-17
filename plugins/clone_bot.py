from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMINS, START_MSG, FORCE_MSG, CUSTOM_CAPTION, FILE_AUTO_DELETE, INDIVIDUAL_AUTO_DELETE, PROTECT_CONTENT, DISABLE_CHANNEL_BUTTON
from database.database import *
import asyncio
import time
import humanize

# Store active bot clients
from bot import cloned_bot_clients, start_cloned_bot

@Client.on_message(filters.command('add_bot') & filters.user(ADMINS) & filters.private)
async def add_bot_handler(client: Client, message: Message):
    """Add a new cloned bot - Only main bot ADMINS can use this"""
    try:
        bot_token = message.text.split(" ", 1)[1]
    except IndexError:
        await message.reply_text(
            "❌ <b>Usage:</b> /add_bot {bot_token}\n\n"
            "<b>Example:</b>\n<code>/add_bot 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz</code>\n\n"
            "Get bot token from @BotFather"
        )
        return
    
    # Check if bot already exists
    existing = await get_cloned_bot(bot_token)
    if existing:
        await message.reply_text("❌ This bot is already added!")
        return
    
    # Test the bot token
    processing_msg = await message.reply_text("⏳ Testing bot token and adding bot...")
    
    try:
        from bot import BotClient
        test_client = BotClient(bot_token, "TestBot")
        await test_client.start()
        bot_me = await test_client.get_me()
        bot_username = bot_me.username
        await test_client.stop()
        
        # Prepare default config from main bot
        default_config = {
            'start_msg': START_MSG,
            'force_sub_msg': FORCE_MSG,
            'custom_caption': CUSTOM_CAPTION,
            'auto_delete_time': FILE_AUTO_DELETE,
            'individual_delete_time': INDIVIDUAL_AUTO_DELETE,
            'protect_content': PROTECT_CONTENT,
            'disable_channel_button': DISABLE_CHANNEL_BUTTON
        }
        
        # Add to database with default config
        bot_id = await add_cloned_bot(bot_token, message.from_user.id, bot_username, default_config)
        
        # Start the bot
        await start_cloned_bot(bot_token)
        
        await processing_msg.edit_text(
            f"✅ <b>Bot @{bot_username} added successfully!</b>\n\n"
            f"<b>🔧 Default Configuration Applied:</b>\n"
            f"• Start Message: Same as main bot ✓\n"
            f"• Force Sub Message: Same as main bot ✓\n"
            f"• Custom Caption: Same as main bot ✓\n"
            f"• Auto Delete Time: {FILE_AUTO_DELETE}s\n"
            f"• Individual Delete Time: {INDIVIDUAL_AUTO_DELETE}s\n"
            f"• Protect Content: {PROTECT_CONTENT}\n"
            f"• Channel Button: {'Disabled' if DISABLE_CHANNEL_BUTTON else 'Enabled'}\n\n"
            f"<b>📝 Next Steps:</b>\n"
            f"1. Go to @{bot_username}\n"
            f"2. Use /settings to configure\n"
            f"3. Set DB Channel\n"
            f"4. Add Force Sub Channels\n\n"
            f"<b>Owner:</b> <code>{message.from_user.id}</code>"
        )
    except Exception as e:
        await processing_msg.edit_text(f"❌ <b>Failed to add bot:</b>\n\n<code>{str(e)}</code>\n\nMake sure the bot token is valid!")

@Client.on_message(filters.command('list_bots') & filters.user(ADMINS) & filters.private)
async def list_bots_handler(client: Client, message: Message):
    """List all cloned bots - Only main bot ADMINS"""
    bots = await get_all_cloned_bots()
    
    if not bots:
        await message.reply_text("❌ No cloned bots found!\n\nUse /add_bot {bot_token} to add a new bot.")
        return
    
    text = "<b>📋 Cloned Bots List:</b>\n\n"
    for i, bot in enumerate(bots, 1):
        status = "✅ Running" if bot['bot_token'] in cloned_bot_clients else "❌ Stopped"
        text += f"<b>{i}. @{bot['bot_username']}</b> {status}\n"
        text += f"   • Owner: <code>{bot['owner_id']}</code>\n"
        text += f"   • DB Channel: <code>{bot['db_channel_id'] or 'Not Set'}</code>\n"
        text += f"   • Force Subs: <code>{len(bot['force_sub_channels'])}</code>\n"
        text += f"   • Admins: <code>{len(bot['admins'])}</code>\n"
        text += f"   • Created: {time.strftime('%Y-%m-%d', time.localtime(bot['created_at']))}\n\n"
    
    text += f"\n<b>Total Bots:</b> {len(bots)}\n"
    text += f"<b>Active Bots:</b> {len([b for b in bots if b['bot_token'] in cloned_bot_clients])}"
    
    await message.reply_text(text)

@Client.on_message(filters.command('remove_bot') & filters.user(ADMINS) & filters.private)
async def remove_bot_handler(client: Client, message: Message):
    """Remove a cloned bot - Only main bot ADMINS"""
    try:
        bot_username = message.text.split(" ", 1)[1].replace("@", "")
    except IndexError:
        await message.reply_text(
            "❌ <b>Usage:</b> /remove_bot @username\n\n"
            "<b>Example:</b>\n<code>/remove_bot @your_cloned_bot</code>"
        )
        return
    
    bot_data = await get_cloned_bot_by_username(bot_username)
    if not bot_data:
        await message.reply_text("❌ Bot not found in database!")
        return
    
    # Confirmation
    confirm_msg = await message.reply_text(
        f"⚠️ <b>Are you sure you want to remove @{bot_username}?</b>\n\n"
        f"This will:\n"
        f"• Stop the bot\n"
        f"• Remove from database\n"
        f"• Delete all bot settings\n\n"
        f"Reply with 'yes' to confirm or 'no' to cancel."
    )
    
    try:
        response = await client.listen(message.from_user.id, timeout=30)
        if response.text.lower() != 'yes':
            await confirm_msg.delete()
            await response.reply_text("❌ Cancelled!")
            return
    except asyncio.TimeoutError:
        await confirm_msg.delete()
        await message.reply_text("⏰ Timeout! Operation cancelled.")
        return
    
    # Stop the bot client
    global cloned_bot_clients
    if bot_data['bot_token'] in cloned_bot_clients:
        try:
            await cloned_bot_clients[bot_data['bot_token']].stop()
            del cloned_bot_clients[bot_data['bot_token']]
        except:
            pass
    
    # Remove from database
    await delete_cloned_bot(bot_data['bot_token'])
    await confirm_msg.delete()
    await response.reply_text(f"✅ Bot @{bot_username} removed successfully!")

@Client.on_message(filters.command('settings') & filters.private)
async def settings_handler(client: Client, message: Message):
    """Show settings panel for cloned bot"""
    # Check if this is a cloned bot
    bot_data = await get_cloned_bot_by_username(client.username)
    
    if not bot_data:
        await message.reply_text(
            "⚠️ <b>This command is only available in cloned bots!</b>\n\n"
            "Use this command in your cloned bot to configure it.\n\n"
            "To add a cloned bot, use /add_bot in the main bot."
        )
        return
    
    # Check if user is admin of this bot
    if message.from_user.id not in bot_data['admins']:
        await message.reply_text(
            "❌ <b>You don't have permission to access settings!</b>\n\n"
            "Only bot admins can use this command.\n\n"
            f"Contact the bot owner: <code>{bot_data['owner_id']}</code>"
        )
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Edit DB Channel", callback_data="setting_db_channel")],
        [InlineKeyboardButton("📢 Manage Force Sub Channels", callback_data="setting_force_subs")],
        [InlineKeyboardButton("💬 Edit Start Message", callback_data="setting_start_msg")],
        [InlineKeyboardButton("⚠️ Edit Force Sub Message", callback_data="setting_force_msg")],
        [InlineKeyboardButton("👥 Manage Admins", callback_data="setting_admins")],
        [InlineKeyboardButton("⏰ Edit Auto Delete Times", callback_data="setting_delete_times")],
        [InlineKeyboardButton("🎨 Edit Custom Caption", callback_data="setting_caption")],
        [InlineKeyboardButton("🔐 Toggle Protect Content", callback_data="setting_protect")],
        [InlineKeyboardButton("🔘 Toggle Channel Button", callback_data="setting_channel_btn")],
        [InlineKeyboardButton("❌ Close", callback_data="close_settings")]
    ])
    
    settings_text = f"""
<b>⚙️ Bot Settings Panel</b>

<b>🤖 Bot:</b> @{client.username}
<b>👤 Owner:</b> <code>{bot_data['owner_id']}</code>

<b>📊 Current Configuration:</b>

<b>Channels & Storage:</b>
• DB Channel: <code>{bot_data['db_channel_id'] or 'Not Set ⚠️'}</code>
• Force Sub Channels: <code>{len(bot_data['force_sub_channels'])}</code>

<b>Access Control:</b>
• Admins: <code>{len(bot_data['admins'])}</code>

<b>Messages:</b>
• Start Message: {'✅ Set' if bot_data['start_msg'] else '❌ Not Set'}
• Force Sub Message: {'✅ Set' if bot_data['force_sub_msg'] else '❌ Not Set'}
• Custom Caption: {'✅ Set' if bot_data['custom_caption'] else '❌ Not Set'}

<b>Auto Delete:</b>
• Bulk: <code>{bot_data['auto_delete_time']}s</code> ({humanize.naturaldelta(bot_data['auto_delete_time'])})
• Individual: <code>{bot_data['individual_delete_time']}s</code> ({humanize.naturaldelta(bot_data['individual_delete_time'])})

<b>Security:</b>
• Protect Content: <code>{'✅ ON' if bot_data['protect_content'] else '❌ OFF'}</code>
• Channel Button: <code>{'❌ Disabled' if bot_data['disable_channel_button'] else '✅ Enabled'}</code>

<b>💡 Tip:</b> Click buttons below to configure each setting.
"""
    
    await message.reply_text(settings_text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r'^setting_'))
async def settings_callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle settings callbacks"""
    bot_data = await get_cloned_bot_by_username(client.username)
    
    if not bot_data:
        await callback_query.answer("⚠️ Not a cloned bot!", show_alert=True)
        return
    
    if callback_query.from_user.id not in bot_data['admins']:
        await callback_query.answer("❌ No permission!", show_alert=True)
        return
    
    action = callback_query.data.replace("setting_", "")
    
    if action == "db_channel":
        await callback_query.message.reply_text(
            "📁 <b>Set DB Channel</b>\n\n"
            "Forward any message from your DB channel or send the channel ID.\n\n"
            "<b>Example:</b> <code>-100123456789</code>\n\n"
            "<b>Requirements:</b>\n"
            "• Bot must be admin in the channel\n"
            "• Bot needs post messages permission\n\n"
            "Send /cancel to cancel."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=60)
            if response.text and response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            if response.forward_from_chat:
                channel_id = response.forward_from_chat.id
            else:
                try:
                    channel_id = int(response.text)
                except:
                    await response.reply_text("❌ Invalid channel ID!")
                    return
            
            # Test channel access
            try:
                await client.get_chat(channel_id)
                test_msg = await client.send_message(channel_id, "✅ DB Channel Test - Bot can access this channel!")
                await test_msg.delete()
                
                await update_cloned_bot(bot_data['bot_token'], {'db_channel_id': channel_id})
                
                # Update client's db_channel attribute
                db_channel = await client.get_chat(channel_id)
                client.db_channel = db_channel
                
                await response.reply_text(
                    f"✅ <b>DB Channel set successfully!</b>\n\n"
                    f"Channel ID: <code>{channel_id}</code>\n"
                    f"Channel: {db_channel.title}\n\n"
                    f"Bot can now store files in this channel!"
                )
            except Exception as e:
                await response.reply_text(
                    f"❌ <b>Error:</b> {str(e)}\n\n"
                    f"<b>Make sure:</b>\n"
                    f"1. Bot is admin in the channel\n"
                    f"2. Bot has 'Post Messages' permission\n"
                    f"3. Channel ID is correct"
                )
        except asyncio.TimeoutError:
            await callback_query.message.reply_text("⏰ Timeout! Please try again.")
    
    elif action == "force_subs":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Channel", callback_data="fsub_add")],
            [InlineKeyboardButton("➖ Remove Channel", callback_data="fsub_remove")],
            [InlineKeyboardButton("📋 List Channels", callback_data="fsub_list")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_settings")]
        ])
        await callback_query.message.edit_text(
            "<b>📢 Manage Force Sub Channels</b>\n\n"
            "<b>Current Channels:</b> {}\n\n"
            "You can add <b>unlimited</b> force subscription channels.\n\n"
            "<b>Features:</b>\n"
            "• Users must join all channels to access bot\n"
            "• Automatic invite link generation\n"
            "• Easy add/remove management\n\n"
            "Choose an action:".format(len(bot_data['force_sub_channels'])),
            reply_markup=keyboard
        )
    
    elif action == "start_msg":
        current_msg = bot_data['start_msg']
        await callback_query.message.reply_text(
            "💬 <b>Set Start Message</b>\n\n"
            f"<b>Current Message:</b>\n{current_msg}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send your new start message.\n\n"
            "<b>📝 Available variables:</b>\n"
            "• <code>{mention}</code> - User mention\n"
            "• <code>{first}</code> - First name\n"
            "• <code>{last}</code> - Last name\n"
            "• <code>{username}</code> - Username\n"
            "• <code>{id}</code> - User ID\n\n"
            "<b>💡 Tip:</b> You can use HTML formatting\n\n"
            "Send /cancel to cancel."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=120)
            if response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            await update_cloned_bot(bot_data['bot_token'], {'start_msg': response.text.html})
            await response.reply_text("✅ Start message updated successfully!")
        except asyncio.TimeoutError:
            await callback_query.message.reply_text("⏰ Timeout!")
    
    elif action == "force_msg":
        current_msg = bot_data['force_sub_msg']
        await callback_query.message.reply_text(
            "⚠️ <b>Set Force Sub Message</b>\n\n"
            f"<b>Current Message:</b>\n{current_msg}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send your new force subscription message.\n\n"
            "<b>📝 Available variables:</b>\n"
            "• <code>{mention}</code> - User mention\n"
            "• <code>{first}</code> - First name\n"
            "• <code>{last}</code> - Last name\n"
            "• <code>{username}</code> - Username\n"
            "• <code>{id}</code> - User ID\n\n"
            "<b>💡 Tip:</b> You can use HTML formatting\n\n"
            "Send /cancel to cancel."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=120)
            if response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            await update_cloned_bot(bot_data['bot_token'], {'force_sub_msg': response.text.html})
            await response.reply_text("✅ Force sub message updated successfully!")
        except asyncio.TimeoutError:
            await callback_query.message.reply_text("⏰ Timeout!")
    
    elif action == "admins":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")],
            [InlineKeyboardButton("➖ Remove Admin", callback_data="admin_remove")],
            [InlineKeyboardButton("📋 List Admins", callback_data="admin_list")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_settings")]
        ])
        await callback_query.message.edit_text(
            "<b>👥 Manage Admins</b>\n\n"
            "<b>Current Admins:</b> {}\n\n"
            "Add or remove bot admins.\n\n"
            "<b>Admin Permissions:</b>\n"
            "• Generate links\n"
            "• Broadcast messages\n"
            "• Manage bot settings\n"
            "• View statistics\n\n"
            "<b>⚠️ Note:</b> Owner cannot be removed\n\n"
            "Choose an action:".format(len(bot_data['admins'])),
            reply_markup=keyboard
        )
    
    elif action == "delete_times":
        await callback_query.message.reply_text(
            "⏰ <b>Set Auto Delete Times</b>\n\n"
            f"<b>Current Settings:</b>\n"
            f"• Bulk Delete: {bot_data['auto_delete_time']}s ({humanize.naturaldelta(bot_data['auto_delete_time'])})\n"
            f"• Individual Delete: {bot_data['individual_delete_time']}s ({humanize.naturaldelta(bot_data['individual_delete_time'])})\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send times in format: <code>bulk_seconds individual_seconds</code>\n\n"
            "<b>📝 Examples:</b>\n"
            "• <code>14400 259200</code> (4 hours bulk, 3 days individual)\n"
            "• <code>3600 86400</code> (1 hour bulk, 1 day individual)\n"
            "• <code>7200 172800</code> (2 hours bulk, 2 days individual)\n\n"
            "<b>💡 Conversion:</b>\n"
            "• 1 hour = 3600s\n"
            "• 1 day = 86400s\n\n"
            "Send /cancel to cancel."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=60)
            if response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            try:
                bulk, individual = map(int, response.text.split())
                await update_cloned_bot(bot_data['bot_token'], {
                    'auto_delete_time': bulk,
                    'individual_delete_time': individual
                })
                await response.reply_text(
                    f"✅ <b>Delete times updated successfully!</b>\n\n"
                    f"Bulk: {bulk}s ({humanize.naturaldelta(bulk)})\n"
                    f"Individual: {individual}s ({humanize.naturaldelta(individual)})"
                )
            except:
                await response.reply_text("❌ Invalid format! Use: bulk_seconds individual_seconds")
        except asyncio.TimeoutError:
            await callback_query.message.reply_text("⏰ Timeout!")
    
    elif action == "caption":
        current_caption = bot_data['custom_caption'] or "Not Set"
        await callback_query.message.reply_text(
            "🎨 <b>Set Custom Caption</b>\n\n"
            f"<b>Current Caption:</b>\n{current_caption}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send your custom caption.\n\n"
            "<b>📝 Available variables:</b>\n"
            "• <code>{previouscaption}</code> - Original caption\n"
            "• <code>{filename}</code> - File name\n"
            "• <code>{mediatype}</code> - Media type\n\n"
            "<b>💡 Example:</b>\n"
            "<code>📁 {filename}\n📊 Type: {mediatype}\n\n{previouscaption}</code>\n\n"
            "Send /cancel to cancel or send <code>remove</code> to remove caption."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=120)
            if response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            caption = None if response.text.lower() == "remove" else response.text.html
            await update_cloned_bot(bot_data['bot_token'], {'custom_caption': caption})
            
            if caption:
                await response.reply_text("✅ Custom caption updated successfully!")
            else:
                await response.reply_text("✅ Custom caption removed!")
        except asyncio.TimeoutError:
            await callback_query.message.reply_text("⏰ Timeout!")
    
    elif action == "protect":
        new_value = not bot_data['protect_content']
        await update_cloned_bot(bot_data['bot_token'], {'protect_content': new_value})
        await callback_query.answer(
            f"✅ Protect Content: {'ON' if new_value else 'OFF'}\n\n"
            f"{'Files cannot be forwarded' if new_value else 'Files can be forwarded'}",
            show_alert=True
        )
        
        # Refresh settings
        from pyrogram.types import Message as Msg
        fake_msg = callback_query.message
        fake_msg.from_user = callback_query.from_user
        await callback_query.message.delete()
        await settings_handler(client, fake_msg)
    
    elif action == "channel_btn":
        new_value = not bot_data['disable_channel_button']
        await update_cloned_bot(bot_data['bot_token'], {'disable_channel_button': new_value})
        await callback_query.answer(
            f"✅ Channel Button: {'Disabled' if new_value else 'Enabled'}\n\n"
            f"{'Share URL button will not be added' if new_value else 'Share URL button will be added'}",
            show_alert=True
        )
        
        # Refresh settings
        from pyrogram.types import Message as Msg
        fake_msg = callback_query.message
        fake_msg.from_user = callback_query.from_user
        await callback_query.message.delete()
        await settings_handler(client, fake_msg)

@Client.on_callback_query(filters.regex(r'^fsub_'))
async def fsub_callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle force sub callbacks"""
    bot_data = await get_cloned_bot_by_username(client.username)
    action = callback_query.data.replace("fsub_", "")
    
    if action == "add":
        await callback_query.message.reply_text(
            "➕ <b>Add Force Sub Channel</b>\n\n"
            "Forward any message from the channel or send channel ID.\n\n"
            "<b>Example:</b> <code>-100123456789</code>\n\n"
            "<b>Requirements:</b>\n"
            "• Bot must be admin in channel\n"
            "• Bot needs 'Invite Users via Link' permission\n\n"
            "Send /cancel to cancel."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=60)
            if response.text and response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            if response.forward_from_chat:
                channel_id = response.forward_from_chat.id
            else:
                try:
                    channel_id = int(response.text)
                except:
                    await response.reply_text("❌ Invalid channel ID!")
                    return
            
            # Get invite link
            try:
                chat = await client.get_chat(channel_id)
                invite_link = chat.invite_link
                if not invite_link:
                    invite_link = await client.export_chat_invite_link(channel_id)
                
                await add_force_sub_channel(bot_data['bot_token'], channel_id, invite_link)
                await response.reply_text(
                    f"✅ <b>Force sub channel added!</b>\n\n"
                    f"Channel ID: <code>{channel_id}</code>\n"
                    f"Channel: {chat.title}\n"
                    f"Invite Link: {invite_link}\n\n"
                    f"Total Force Sub Channels: {len(bot_data['force_sub_channels']) + 1}"
                )
            except Exception as e:
                await response.reply_text(
                    f"❌ <b>Error:</b> {str(e)}\n\n"
                    f"Make sure:\n"
                    f"• Bot is admin in the channel\n"
                    f"• Bot has 'Invite Users via Link' permission!"
                )
        except asyncio.TimeoutError:
            await callback_query.message.reply_text("⏰ Timeout!")
    
    elif action == "remove":
        channels = bot_data['force_sub_channels']
        if not channels:
            await callback_query.answer("No channels to remove!", show_alert=True)
            return
        
        text = "➖ <b>Remove Channel</b>\n\nSend the channel ID to remove:\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. <code>{ch['channel_id']}</code>\n"
        text += "\nSend /cancel to cancel."
        
        await callback_query.message.reply_text(text)
        try:
            response = await client.listen(callback_query.from_user.id, timeout=60)
            if response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            channel_id = int(response.text)
            await remove_force_sub_channel(bot_data['bot_token'], channel_id)
            await response.reply_text(
                f"✅ <b>Channel removed!</b>\n\n"
                f"Channel ID: <code>{channel_id}</code>\n\n"
                f"Remaining Force Sub Channels: {len(bot_data['force_sub_channels']) - 1}"
            )
        except:
            await callback_query.message.reply_text("❌ Invalid channel ID!")
    
    elif action == "list":
        channels = bot_data['force_sub_channels']
        if not channels:
            await callback_query.answer("No channels configured!", show_alert=True)
            return
        
        text = "📋 <b>Force Sub Channels:</b>\n\n"
        for i, ch in enumerate(channels, 1):
            try:
                chat = await client.get_chat(ch['channel_id'])
                text += f"{i}. <b>{chat.title}</b>\n"
                text += f"   ID: <code>{ch['channel_id']}</code>\n"
                text += f"   Link: {ch['invite_link']}\n\n"
            except:
                text += f"{i}. <code>{ch['channel_id']}</code>\n"
                text += f"   Link: {ch['invite_link']}\n\n"
        
        text += f"<b>Total:</b> {len(channels)} channels"
        await callback_query.message.reply_text(text)

@Client.on_callback_query(filters.regex(r'^admin_'))
async def admin_callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle admin management callbacks"""
    bot_data = await get_cloned_bot_by_username(client.username)
    action = callback_query.data.replace("admin_", "")
    
    if action == "add":
        await callback_query.message.reply_text(
            "➕ <b>Add Admin</b>\n\n"
            "Send user ID or forward a message from the user.\n\n"
            "<b>Example:</b> <code>123456789</code>\n\n"
            "<b>Admin will have access to:</b>\n"
            "• Generate links\n"
            "• Broadcast messages\n"
            "• View statistics\n"
            "• All bot features\n\n"
            "Send /cancel to cancel."
        )
        try:
            response = await client.listen(callback_query.from_user.id, timeout=60)
            if response.text and response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            if response.forward_from:
                admin_id = response.forward_from.id
            else:
                admin_id = int(response.text)
            
            if admin_id in bot_data['admins']:
                await response.reply_text("⚠️ This user is already an admin!")
                return
            
            await add_bot_admin(bot_data['bot_token'], admin_id)
            await response.reply_text(
                f"✅ <b>Admin added!</b>\n\n"
                f"User ID: <code>{admin_id}</code>\n\n"
                f"Total Admins: {len(bot_data['admins']) + 1}"
            )
        except:
            await callback_query.message.reply_text("❌ Invalid user ID!")
    
    elif action == "remove":
        admins = bot_data['admins']
        if len(admins) <= 1:
            await callback_query.answer("Cannot remove all admins!", show_alert=True)
            return
        
        text = "➖ <b>Remove Admin</b>\n\nSend user ID to remove:\n\n"
        for i, admin_id in enumerate(admins, 1):
            owner_tag = " 👑 (Owner)" if admin_id == bot_data['owner_id'] else ""
            text += f"{i}. <code>{admin_id}</code>{owner_tag}\n"
        text += "\n⚠️ Note: You cannot remove the owner!\n\nSend /cancel to cancel."
        
        await callback_query.message.reply_text(text)
        try:
            response = await client.listen(callback_query.from_user.id, timeout=60)
            if response.text == "/cancel":
                await response.reply_text("❌ Cancelled!")
                return
            
            admin_id = int(response.text)
            
            if admin_id == bot_data['owner_id']:
                await response.reply_text("❌ Cannot remove owner!")
                return
            
            if admin_id not in admins:
                await response.reply_text("⚠️ This user is not an admin!")
                return
            
            await remove_bot_admin(bot_data['bot_token'], admin_id)
            await response.reply_text(
                f"✅ <b>Admin removed!</b>\n\n"
                f"User ID: <code>{admin_id}</code>\n\n"
                f"Remaining Admins: {len(admins) - 1}"
            )
        except:
            await callback_query.message.reply_text("❌ Invalid user ID!")
    
    elif action == "list":
        admins = bot_data['admins']
        text = "📋 <b>Bot Admins:</b>\n\n"
        for i, admin_id in enumerate(admins, 1):
            owner_tag = " 👑" if admin_id == bot_data['owner_id'] else ""
            try:
                user = await client.get_users(admin_id)
                name = user.first_name + (f" {user.last_name}" if user.last_name else "")
                text += f"{i}. {name}{owner_tag}\n"
                text += f"   ID: <code>{admin_id}</code>\n"
                text += f"   Username: @{user.username if user.username else 'None'}\n\n"
            except:
                text += f"{i}. <code>{admin_id}</code>{owner_tag}\n\n"
        
        text += f"<b>Total:</b> {len(admins)} admins"
        await callback_query.message.reply_text(text)

@Client.on_callback_query(filters.regex(r'^close_settings$'))
async def close_settings_handler(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await callback_query.answer("Settings closed!", show_alert=False)

@Client.on_callback_query(filters.regex(r'^back_to_settings$'))
async def back_to_settings_handler(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    # Recreate settings message
    from pyrogram.types import Message as Msg
    fake_msg = callback_query.message
    fake_msg.from_user = callback_query.from_user
    await settings_handler(client, fake_msg)
