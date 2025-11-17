#(©)AnimeXyz

from aiohttp import web
from plugins import web_server

import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from database.database import get_all_cloned_bots, get_cloned_bot

from config import API_HASH, APP_ID, LOGGER, TG_BOT_TOKEN, TG_BOT_WORKERS, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, CHANNEL_ID, PORT

name = """
 BY MIKEY FROM TG
"""

# Global dictionary to store cloned bot clients
cloned_bot_clients = {}

class BotClient(Client):
    """Custom client for both main and cloned bots"""
    def __init__(self, bot_token, session_name="Bot"):
        super().__init__(
            name=session_name,
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=bot_token
        )
        self.LOGGER = LOGGER
        self.bot_token = bot_token

class Bot(BotClient):
    def __init__(self):
        super().__init__(TG_BOT_TOKEN, "MainBot")

    async def start(self):
        await super().start()
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
        
        # Start all cloned bots from database
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
        """Start all cloned bots from database"""
        cloned_bots = await get_all_cloned_bots()
        for bot_data in cloned_bots:
            try:
                await start_cloned_bot(bot_data['bot_token'])
                self.LOGGER(__name__).info(f"✅ Cloned bot started: @{bot_data['bot_username']}")
            except Exception as e:
                self.LOGGER(__name__).error(f"❌ Failed to start cloned bot @{bot_data['bot_username']}: {e}")

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
    """Start a single cloned bot"""
    global cloned_bot_clients
    
    if bot_token in cloned_bot_clients:
        return cloned_bot_clients[bot_token]  # Already running
    
    try:
        bot_data = await get_cloned_bot(bot_token)
        if not bot_data:
            return None
        
        # Create client
        client = BotClient(bot_token, f"ClonedBot_{bot_data['bot_username']}")
        await client.start()
        
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
    except Exception as e:
        print(f"Error starting cloned bot: {e}")
        return None
