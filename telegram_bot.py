#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, wrong-import-position
"""
In this file, the TelegramBot class is defined. Usage: Send /start to initiate
the conversation on Telegram. Press Ctrl-C on the command line to stop the bot.
"""

import os, asyncio, requests
from helpers import log, df_to_csv, csv_to_df
from typing import Dict, List
from dotenv import load_dotenv
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    PersistenceInput,
    filters,
)

load_dotenv("./.env")
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
out_csv = 'known_users.csv'    # 2 cols: Starknet Address, Total Contribution Points

class TelegramBot:
    """A class to encapsulate all relevant methods of the Telegram bot."""

    def __init__(self, debug_mode=False):
        """
        Constructor of the class. Initializes certain instance variables.
        """
        # The bot data file
        self.data_path = "./data"
        # The contributor data file
        self.input_data_path = "./input_data.csv"
        # Switch on logging of bot data & callback data (inline button presses) for debugging
        self.debug_mode = debug_mode
        # Set up conversation states & inline keyboard
        self.CHOOSING, self.TYPING_REPLY = range(2)
        reply_keyboard = [
            ["Authenticate Discord", "Authenticate Twitter"],
            ["Done"]
        ]
        self.markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        self.application = None



    def parse_str(self, user_data) -> str:
        """Helper function for formatting the gathered user info."""
        out_list = []
        # Only show non-empty values
        for key, value in user_data.items():
            if value not in [set(), [], None, ""]:
                out_list.append(f"{key} - {value}")
        return "\n".join(out_list).join(["\n", "\n"])


    async def send_msg(self, msg, update, **kwargs) -> None:
        """Wrapper function to send out messages in all conditions."""

        if update.message:
            await update.message.reply_text(msg, **kwargs)
        else:
            await update._bot.send_message(update.effective_message.chat_id, msg, **kwargs)


    async def csv(self, update, context) -> None:
        """Returns csv containing only wallet <-> total points pairs."""
        # TODO
        
        # Generate out_csv
        pass


    async def start_wrapper(self, update, context) -> int:
        """Necessary for Oauth2 flow. Calls either menu or Discord/Twitter verification."""

        user_data = context.user_data

        if self.debug_mode:
            msg = (
                f"start_wrapper():\n"
                f"context.args: {context.args}\n"
                f"update: {update}\n"
                f"context: {context}\n"
            )
            log(msg)

        # Case: /start command resulting from oauth deep link
        if context.args not in ([], None):
            auth_code = context.args

            print("start_wrapper() context.args:", context.args)


            if user_data["choice"] == "discord auth":

                if self.debug_mode:
                    log(f"choice: {user_data['choice']}. Calling self.discord_oauth_get_data(auth_code, update, context)")

                return await self.discord_oauth_get_data(auth_code, update, context)
        
            if user_data["choice"] == "twitter auth":

                if self.debug_mode:
                    log(f"choice: {user_data['choice']}. Calling self.twitter_oauth_get_data(auth_code, update, context)")

                    return await self.twitter_oauth_get_data(auth_code, update, context)


        # Case: Typical /start command press
        else:
            if self.debug_mode: log("Calling self.start()")
            return await self.start(update, context)


    async def start(self, update, context) -> int:
        """Start the conversation & button menu."""

        chat_id = update.message.chat_id if update.message else context._chat_id
        user_data = context.user_data

        reply_text = (
            "Have you contributed to JediSwap?"
            " If you are a Dev, Community Manager, Problem Solver, "
            " or Designer, please authenticate your /discord handle."
            " If you tweeted about JediSwap, please authenticate your"
            " /twitter handle."
            " Please choose:"
        )
        # Send out message & end it here
        await self.send_msg(reply_text, update, reply_markup=self.markup)
        return self.CHOOSING


    async def received_information(self, update, context) -> int:
        """
        Handling of user replies happens here, depending on data, category
        and callback data, if available.
        Options for context.user_data["choice"]:
        "add wallet", "discord auth", "twitter auth"
        """

        text = update.message.text
        user_data = context.user_data
        category = user_data["choice"]

        # Default callback data: None
        if "last callback" not in context.user_data: context.user_data["last callback"] = None
        callback_data = context.user_data["last callback"]

        if self.debug_mode:
            log(
                f"received_information() CALLBACK_DATA: {callback_data}\n"
                f"received_information() CATEGORY: {category}\n"
                f"received_information() UPDATE.CALLBACK_QUERY: {update.callback_query}"
            )

        if category == "add wallet":
            
            # TODO: Check for the right format (length + character types (only numbers and letters Aa-Hh))
            # ETH: web3-validator package -> ethers.utils.isAddress(addy)
            # Starknet: ?

            # TODO: Check starkscan API for existence of wallet, return False if not existing
            right_format = True
            exists_onchain = True
            valid_wallet = (right_format and exists_onchain)

            # If wallet not existing or entered data invalid -> Repeat prompt with notice.
            if not valid_wallet:

                reply_text = (
                    f"Couldn't find {text} on Starknet."
                    " Please make sure the entered wallet is correct."
                    " You'll have to authenticate again to start over."
                    " Please choose to verify your /discord or /twitter"
                    " handle."
                )

                await self.send_msg(
                    reply_text,
                    update,
                    disable_web_page_preview=True,
                    parse_mode="Markdown"
                )

                return self.CHOOSING

            # If valid wallet entered -> Add wallet to data, remove Discord/Twitter handle
            else:

                # TODO: Add wallet information to target row. Then delete username information
                wallet = text
                handle = user_data["handle"]
                platform = user_data["platform"]

                # Add wallet information to data & delete handle information
                await self.replace_handle_with_wallet(wallet, platform, handle, update, context)
                
                reply_text = (
                    "Success! Your contribution points have been attatched"
                    f" to {wallet}! Congratulations!"
                    f" Keep in mind that you will no longer be able to"
                    f" find yourself with this tool using the handle {handle}"
                    f" since it hs been replaced in the data."
                )

                await self.send_msg(
                    reply_text,
                    update,
                    disable_web_page_preview=True,
                    parse_mode="Markdown"
                )

                return self.CHOOSING


    async def replace_handle_with_wallet(self, wallet, platform, handle, update, context):
        """
        Add wallet information to row in data. Delete handle information
        """

        df = csv_to_df(self.input_data_path)

        if platform == "discord":
            target_col = "Discord Username"
        if platform == "twitter":
            target_col = "Twitter Username"

        # Add wallet info
        df.loc[df[target_col] == handle, "Wallet"] = wallet

        # Delete handle info
        df.loc[df[target_col] == handle, target_col] = ""

        # Update data file
        df_to_csv(df, self.input_data_path + "_OUT")

        return


    async def authenticate_discord(self, update, context) -> None:
        """
        Redirect user to Oauth2 verification page. Result can be fetched
        from inline callback data.
        """
        user_data = context.user_data
        user_data["choice"] = "discord auth"

        def build_oauth_link():
            client_id = os.getenv("OAUTH_DISCORD_CLIENT_ID")
            redirect_uri = os.getenv("OAUTH_REDIRECT_URI")
            scope = "identify"
            discord_login_url = f"https://discordapp.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
            return discord_login_url

        oauth_link = build_oauth_link()

        msg = (
            f"Please follow this [link]({oauth_link}) to login with Discord,"
            f" then hit the start that'll appear once you get redirected back.\n\n"
            f" (For ios users: Due to a [bug](https://github.com/TelegramMessenger/Telegram-iOS/issues/1100) in the recent"
            f" Telegram ios app release, you need to first click the [link]({oauth_link}), which will open a browser,"
            f" then switch back to the Telegram app, close it temporarily, return to the browser and "
            f" only then hit 'Open in Telegram'.)"
        )

        await self.send_msg(
            msg,
            update,
            disable_web_page_preview=True,
            parse_mode="Markdown",
            )

        return


    async def authenticate_twitter(self, update, context) -> None:
        """
        Redirect user to Oauth2 verification page. Result can be fetched
        from inline callback data.
        """
        user_data = context.user_data
        user_data["choice"] = "twitter auth"

        def build_oauth_link():
            client_id = os.getenv("OAUTH_DISCORD_CLIENT_ID")
            redirect_uri = os.getenv("OAUTH_REDIRECT_URI")
            scope = "identify"
            discord_login_url = f"https://discordapp.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
            return discord_login_url

        oauth_link = build_oauth_link()

        msg = (
            f"Please follow this [link]({oauth_link}) to login with Discord,"
            f" then hit the start button once it appears here ⬇️"
        )

        await self.send_msg(
            msg,
            update,
            disable_web_page_preview=True,
            parse_mode="Markdown",
            )

        return


    async def discord_oauth_get_data(self, auth_code, update, context) -> None:
        """Queries Discord API using received auth_code for user name."""

        context.args = []    # Delete received Oauth code from context object

        def build_oauth_obj():
            d = {}
            d["client_id"] = os.getenv("OAUTH_DISCORD_CLIENT_ID")
            d["client_secret"] = os.getenv("OAUTH_DISCORD_CLIENT_SECRET")
            d["redirect_uri"] = os.getenv("OAUTH_REDIRECT_URI")
            d["scope"] = 'identify'
            d["discord_login_url"] = f'https://discordapp.com/api/oauth2/authorize?client_id={d["client_id"]}&redirect_uri={d["redirect_uri"]}&response_type=code&scope={d["scope"]}'
            d["discord_token_url"] = 'https://discordapp.com/api/oauth2/token'
            d["discord_api_url"] = 'https://discordapp.com/api'
            return d

        def get_accesstoken(auth_code, oauth):
            payload = {
                "client_id": oauth["client_id"],
                "client_secret": oauth["client_secret"],
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": oauth["redirect_uri"],
                "scope": oauth["scope"]
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            access_token = requests.post(
                url = oauth["discord_token_url"],
                data=payload,
                headers=headers
            )

            json = access_token.json()
            return json.get("access_token")

        def get_userjson(access_token, oauth):
            url = oauth["discord_api_url"]+'/users/@me'
            headers = {"Authorization": f"Bearer {access_token}"}
            user_obj = requests.get(url=url, headers=headers)
            user_json = user_obj.json()
            return user_json

        oauth = build_oauth_obj()
        access_token = get_accesstoken(auth_code, oauth)
        user_json = get_userjson(access_token, oauth)

        username = user_json.get('username')
        discriminator = user_json.get('discriminator')
        #user_id = user_json.get('id')

        if discriminator in (None, 0, '0'):
            complete_name = str(username)
        else:
            complete_name = str(username)+"#"+str(discriminator)

        # Store handle in bot user data
        context.user_data["handle"] = complete_name
        context.user_data["platform"] = "discord"

        if self.debug_mode:
            log(f"GOT DISCORD OAUTH INFO: {complete_name} ")

        reply_msg = (
            f"Success! {complete_name} verified!"
            " Time to enter your wallet information!"
        )

        await self.send_msg(reply_msg, update)
        await asyncio.sleep(1.5)
        return await self.add_wallet(update, context, platform="discord", handle=complete_name)


    async def twitter_oauth_get_data(self, auth_code, update, context) -> None:
        """Queries Discord API using received auth_code for user name."""

        context.args = []    # Delete received Oauth code from context object

        def build_oauth_obj():
            d = {}
            d["client_id"] = os.getenv("OAUTH_DISCORD_CLIENT_ID")
            d["client_secret"] = os.getenv("OAUTH_DISCORD_CLIENT_SECRET")
            d["redirect_uri"] = os.getenv("OAUTH_REDIRECT_URI")
            d["scope"] = 'identify'
            d["discord_login_url"] = f'https://discordapp.com/api/oauth2/authorize?client_id={d["client_id"]}&redirect_uri={d["redirect_uri"]}&response_type=code&scope={d["scope"]}'
            d["discord_token_url"] = 'https://discordapp.com/api/oauth2/token'
            d["discord_api_url"] = 'https://discordapp.com/api'
            return d

        def get_accesstoken(auth_code, oauth):
            payload = {
                "client_id": oauth["client_id"],
                "client_secret": oauth["client_secret"],
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": oauth["redirect_uri"],
                "scope": oauth["scope"]
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            access_token = requests.post(
                url = oauth["discord_token_url"],
                data=payload,
                headers=headers
            )

            json = access_token.json()
            return json.get("access_token")

        def get_userjson(access_token, oauth):
            url = oauth["discord_api_url"]+'/users/@me'
            headers = {"Authorization": f"Bearer {access_token}"}
            user_obj = requests.get(url=url, headers=headers)
            user_json = user_obj.json()
            return user_json

        oauth = build_oauth_obj()
        access_token = get_accesstoken(auth_code, oauth)
        user_json = get_userjson(access_token, oauth)

        username = user_json.get('username')
        discriminator = user_json.get('discriminator')
        #user_id = user_json.get('id')

        if discriminator in (None, 0, '0'):
            complete_name = str(username)
        else:
            complete_name = str(username)+"#"+str(discriminator)

        # Store handle in bot user data
        context.user_data["handle"] = complete_name
        context.user_data["platform"] = "twitter"

        if self.debug_mode:
            log(f"GOT TWITTER OAUTH INFO: {complete_name} ")

        reply_msg = (
            f"Success! {complete_name} verified!"
            " Time to enter your wallet information!"
        )

        await self.send_msg(reply_msg, update)
        await asyncio.sleep(1.5)
        return await self.add_wallet(update, context, platform="twitter", handle=complete_name)


    async def add_wallet(self, update, context, platform, handle) -> int:
        """
        Starknet wallet is added here. This is an irreversible step.
        Once a wallet is entered, the handle information in the data is deleted.
        """

        context.user_data["choice"] = "add wallet"

        # Prompt for Wallet

        reply_text = (
            f"Please enter a Starknet address you own to replace the"
            f" {platform} handle '{handle}'. Note that this is irreversible!"
            f" Going forward, your contribution points will forever be connected to"
            f" this address instead of the handle '{handle}', so make sure you enter it right!"
            f" Or hit /menu to go back."
        )
        await self.send_msg(reply_text, update)
        return self.TYPING_REPLY


    async def show_source(self, update, context) -> None:
        """Display link to github."""
        await self.send_msg(
            "Collaboration welcome! -> [github](https://github.com/jediswaplabs/contributor-nft-bot)"
            "\nBack to /menu or /done.",
            update,
            parse_mode="Markdown"
        )
        return ConversationHandler.END


    async def csv(self, update, context) -> None:
        """Admin only: Return a csv containing wallet<->total points data."""

        chat_id = update.message.chat_id if update.message else context._chat_id
        admin_id = int(os.environ["ADMIN_ID"])

        if chat_id == admin_id:

            msg = (
                f"UNDER CONSTRUCTION"
            )

        else:
            msg = (
                f"\nSorry, you are not authorized."
                f"\n\n/menu  |  /done  |  /github"
            )

        await self.send_msg(msg, update)
        return ConversationHandler.END
        

    async def done(self, update, context) -> int:
        """End the conversation woth a message how to bring back the menu."""
        user_data = context.user_data

        if "choice" in user_data:
            del user_data["choice"]

        await self.send_msg(
            "Bring back the /menu anytime!",
            update,
            reply_markup=ReplyKeyboardRemove(),
        )

        return ConversationHandler.END


    def run(self) -> None:
        """Run the bot with all handlers as defined."""

        # Some config for the application
        config = PersistenceInput(
            bot_data=False,
            chat_data=False,
            user_data=False,
            callback_data=False
        )
        persistence = PicklePersistence(
            filepath=self.data_path,
            store_data=config,
            update_interval=30
        )
        # Create the application and pass it your bot's token.
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.application = (
            Application.builder().token(token).persistence(persistence).build()
        )

        # Define conversation handler with the states CHOOSING and TYPING_REPLY
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start_wrapper),
                CommandHandler("menu", self.start_wrapper),
            ],
            states={
                self.CHOOSING: [
                    MessageHandler(filters.Regex("^Authenticate Discord$"),
                        self.authenticate_discord
                    ),
                    MessageHandler(filters.Regex("^Authenticate Twitter$"),
                        self.authenticate_twitter
                    ),
                    CommandHandler("start",
                        self.start_wrapper
                    )
                    

                ],
                self.TYPING_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~(filters.COMMAND | filters.Regex("^(back|Done|menu)$")),
                        self.received_information
                    ),
                    MessageHandler(
                        filters.Regex("^menu$"),
                        self.start_wrapper
                    ),
                    MessageHandler(
                        filters.COMMAND,
                        self.start_wrapper
                    ),
                    CommandHandler("start",
                        self.start_wrapper
                    )
                ],
            },
            fallbacks=[
                MessageHandler(
                    filters.Regex("^Done$"),
                    self.done
                ),
                CommandHandler(
                    "menu",
                    self.start_wrapper
                ),
                CommandHandler(
                    "done",
                    self.done
                )
            ],
            name="my_conversation",
            persistent=False,
        )

        # Add additional handlers
        self.application.add_handler(conv_handler)

        start_handler = CommandHandler("start", self.start_wrapper)
        discord_auth_handler = CommandHandler("discord", self.authenticate_discord)
        twitter_auth_handler = CommandHandler("twitter", self.authenticate_twitter)
        show_source_handler = CommandHandler("github", self.show_source)
        csv_handler = CommandHandler("csv", self.csv)

        self.application.add_handler(start_handler)
        self.application.add_handler(discord_auth_handler)
        self.application.add_handler(twitter_auth_handler)
        self.application.add_handler(show_source_handler)
        self.application.add_handler(csv_handler)

        # Run application
        log("TEST LOGGING")
        self.application.run_polling()
