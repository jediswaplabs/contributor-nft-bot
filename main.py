#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script is running a Telegram bot as a frontend for user data entry.
The bot logic is defined in ./telegram_bot.py.
Written by Al Matty - github.com/al-matty
"""

import logging
from telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(format="%(asctime)s :\n%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Toggle more extensive logging (bot data, Discord messages, TG inline button presses)
debug_mode = True

from helpers import log
print("print test")
log("log test")

# Instantiate & run bot
tg_bot = TelegramBot(debug_mode=debug_mode)
tg_bot.run()

