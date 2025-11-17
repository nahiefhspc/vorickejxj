#(©)AnimeXyz

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
import sys
import asyncio
from datetime import datetime
from database.database import get_all_cloned_bots, get_cloned_bot

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, CHANNEL_ID, PORT

name = """
 BY MIKEY FROM TG
"""

# Global dictionary to store cloned bot clients
cloned_bot_clients = {}

class BotClient(Client):
    """Custom client for both main and cloned bots with FloodWait handling"""
    def __init__(self, bot_token, session_name="Bot"):
        super().__init__(
            name=session_name,
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=bot_token,
            sleep_threshold=30  # Sleep threshold for FloodWait
        )
        self.LOGGER = LOGGER
        self.bot_token = bot_token
    
    async def start_with_retry(self, max_retries=3):
        """Start bot with FloodWait retry logic"""
        for attempt in range(max_retries):
            try:
                await super().start()
                return True
            except FloodWait as e:
                self.LOGGER(__name__).warning(f"FloodWait: Waiting {e.value} seconds (Attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(e.value)
                else:
                    self.LOGGER(__name__).error(f"Max retries reached. Please wait {e.value} seconds and restart.")
                    raise
            except Exception as e:
                self.LOGGER(__name__).error(f"Error starting bot: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    raise
        return False

class Bot(BotClient):
    def __init__(self):
        super().__init__(TG_BOT_TOKEN, "MainBot")

    async def start(self):
        # Start with FloodWait handling
        try:
            success = await self.start_with_retry()
            if not success:
                self.LOGGER(__name__).error("Failed to start bot after retries")
                sys.exit()
        except FloodWait as e:
            self.LOGGER(__name__).error(f"FloodWait: Please wait {e.value} seconds and try again")
            sys.exit()
        except Exception as e:
            self.LOGGER(__name__).error(f"Critical error: {e}")
            sys.exit()
        
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()
        self.username = usr_bot_me.username

        # Setup main bot force sub channels
        if FORCE_SUB_CHANNEL:
            try:
                link = (await self.get_chat(FORCE_SUB_CHANNEL)).invite_link
                if not link:
                    await self.export_chat_invite_link(FORCE_SUB_CHANNEL)
                    link = (await self.get_chat(FORCE_SUB_CHANNEL)).invite_link
                self.invitelink = link
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning("Bot can't Export Invite link from Force Sub Channel!")
                self.LOGGER(__name__).warning(f"Please Double check the FORCE_SUB_CHANNEL value and Make sure Bot is Admin in channel with Invite Users via Link Permission, Current Force Sub Channel Value: {FORCE_SUB_CHANNEL}")
                self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/weebs_support for support")
                sys.exit()
        
        if FORCE_SUB_CHANNEL2:
            try:
                link = (await self.get_chat(FORCE_SUB_CHANNEL2)).invite_link
                if not link:
                    await self.export_chat_invite_link(FORCE_SUB_CHANNEL2)
                    link = (await self.get_chat(FORCE_SUB_CHANNEL2)).invite_link
                self.invitelink2 = link
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning("Bot can't Export Invite link from Force Sub Channel 2!")
                self.LOGGER(__name__).warning(f"Please Double check the FORCE_SUB_CHANNEL2 value and Make sure Bot is Admin in channel with Invite Users via Link Permission, Current Force Sub Channel Value: {FORCE_SUB_CHANNEL2}")
                self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/weebs_support for support")
                sys.exit()
        
        if FORCE_SUB_CHANNEL3:
            try:
                link = (await self.get_chat(FORCE_SUB_CHANNEL3)).invite_link
                if not link:
                    await self.export_chat_invite_link(FORCE_SUB_CHANNEL3)
                    link = (await self.get_chat(FORCE_SUB_CHANNEL3)).invite_link
                self.invitelink3 = link
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning("Bot can't Export Invite link from Force Sub Channel 3!")
                self.LOGGER(__name__).warning(f"Please Double check the FORCE_SUB_CHANNEL3 value and Make sure Bot is Admin in channel with Invite Users via Link Permission, Current Force Sub Channel Value: {FORCE_SUB_CHANNEL3}")
                self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/weebs_support for support")
                sys.exit()

        if FORCE_SUB_CHANNEL4:
            try:
                link = (await self.get_chat(FORCE_SUB_CHANNEL4)).invite_link
                if not link:
                    await self.export_chat_invite_link(FORCE_SUB_CHANNEL4)
                    link = (await self.get_chat(FORCE_SUB_CHANNEL4)).invite_link
                self.invitelink4 = link
            except Exception as a:
                self.LOGGER(__name__).warning(a)
                self.LOGGER(__name__).warning("Bot can't Export Invite link from Force Sub Channel 4!")
                self.LOGGER(__name__).warning(f"Please Double check the FORCE_SUB_CHANNEL4 value and Make sure Bot is Admin in channel with Invite Users via Link Permission, Current Force Sub Channel Value: {FORCE_SUB_CHANNEL4}")
                self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/weebs_support for support")
                sys.exit()     
     
        # Setup DB Channel
        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(chat_id=db_channel.id, text="Test Message")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(f"Make Sure bot is Admin in DB Channel, and Double check the CHANNEL_ID Value, Current Value {CHANNEL_ID}")
            self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/weebs_support for support")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Main Bot Running: @{self.username}")
        
        # Start all cloned bots from database (with delay to avoid FloodWait)
        await self.start_all_cloned_bots()
        
        # Web server
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()
        
        self.LOGGER(__name__).info(f"""       

  ___ ___  ___  ___ ___ _    _____  _____  ___ _____ ___ 
 / __/ _ \|   \| __| __| |  |_ _\ \/ / _ )/ _ \_   _/ __|
| (_| (_) | |) | _|| _|| |__ | | >  <| _ \ (_) || | \__ \\
 \___\___/|___/|___|_| |____|___/_/\_\___/\___/ |_| |___/
                                                         
                                          """)

    async def start_all_cloned_bots(self):
        """Start all cloned bots from database with delay between each"""
        cloned_bots = await get_all_cloned_bots()
        total_bots = len(cloned_bots)
        
        if total_bots == 0:
            self.LOGGER(__name__).info("No cloned bots found in database")
            return
        
        self.LOGGER(__name__).info(f"Found {total_bots} cloned bots. Starting them with 5-second delay...")
        
        for i, bot_data in enumerate(cloned_bots, 1):
            try:
                self.LOGGER(__name__).info(f"Starting cloned bot {i}/{total_bots}: @{bot_data['bot_username']}")
                await start_cloned_bot(bot_data['bot_token'])
                self.LOGGER(__name__).info(f"✅ Cloned bot started: @{bot_data['bot_username']}")
                
                # Add delay between bot starts to avoid FloodWait
                if i < total_bots:
                    self.LOGGER(__name__).info(f"Waiting 5 seconds before starting next bot...")
                    await asyncio.sleep(5)
                    
            except FloodWait as e:
                self.LOGGER(__name__).warning(f"FloodWait for @{bot_data['bot_username']}: Waiting {e.value} seconds")
                await asyncio.sleep(e.value)
                # Retry after waiting
                try:
                    await start_cloned_bot(bot_data['bot_token'])
                    self.LOGGER(__name__).info(f"✅ Cloned bot started after FloodWait: @{bot_data['bot_username']}")
                except Exception as retry_error:
                    self.LOGGER(__name__).error(f"❌ Failed to start @{bot_data['bot_username']} after FloodWait: {retry_error}")
            except Exception as e:
                self.LOGGER(__name__).error(f"❌ Failed to start cloned bot @{bot_data['bot_username']}: {e}")
        
        self.LOGGER(__name__).info(f"Cloned bots startup complete. Active: {len(cloned_bot_clients)}/{total_bots}")

    async def stop(self, *args):
        await super().stop()
        # Stop all cloned bots
        global cloned_bot_clients
        for bot_client in cloned_bot_clients.values():
            try:
                await bot_client.stop()
            except:
                pass
        self.LOGGER(__name__).info("All bots stopped.")

async def start_cloned_bot(bot_token: str):
    """Start a single cloned bot with FloodWait handling"""
    global cloned_bot_clients
    
    if bot_token in cloned_bot_clients:
        return cloned_bot_clients[bot_token]  # Already running
    
    try:
        bot_data = await get_cloned_bot(bot_token)
        if not bot_data:
            return None
        
        # Create client with unique session name
        session_name = f"ClonedBot_{bot_data['bot_username']}"
        client = BotClient(bot_token, session_name)
        
        # Start with retry logic
        success = await client.start_with_retry(max_retries=2)
        if not success:
            return None
        
        # Setup bot attributes
        bot_me = await client.get_me()
        client.username = bot_me.username
        client.uptime = datetime.now()
        
        # Setup DB Channel if configured
        if bot_data.get('db_channel_id'):
            try:
                db_channel = await client.get_chat(bot_data['db_channel_id'])
                client.db_channel = db_channel
            except Exception as e:
                print(f"Failed to setup DB channel for {bot_data['bot_username']}: {e}")
        
        # Setup force sub links
        for i, channel_data in enumerate(bot_data.get('force_sub_channels', []), 1):
            setattr(client, f'invitelink{i if i > 1 else ""}', channel_data['invite_link'])
        
        # Set parse mode
        client.set_parse_mode(ParseMode.HTML)
        
        # Store client
        cloned_bot_clients[bot_token] = client
        
        return client
    except FloodWait as e:
        print(f"FloodWait error starting cloned bot: {e.value} seconds")
        raise
    except Exception as e:
        print(f"Error starting cloned bot: {e}")
        return None
