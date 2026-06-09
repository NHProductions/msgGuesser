# -------- Bot Settings -----------
token = "" # REQUIRED: Token that discord will use for your bot to be actually working.
saveFile = "" # File that save data will be. To disable saving, set saveFile to an empty string.
saveInterval = 10 # Interval in seconds for saving the data.
adminUser = "" # User that can rule ?saveAll & ?close.
cmdPrefix = '?' # Command prefix; e.x ?start.
# -------- Default Settings for servers --------
defaultGuessingTime = 10;
defaultPingsOnly = False
defaultmsgLimit = 500;
defaultIncludeAttachments = True;
defaultMaxGuesses = 1;
defaultMsgPing = 1;
# Cosmetic stuff:
loadingBarAmt = 25; # Amount of bars within the progress bar.
progFilled = "■" # Character that shows when a cell is filled in the progress bar; (This means you could include emojis, by having it be "<:emojiName:id>")
progNotFilled = "□" # character that shows when a cell isn't filled in the progress bar;
haveProgressBar = True # If there should be a progress bar in the message
haveProgressMessage = True # If the bot's "Gathering Message" will include "x/xx"
haveGatheringMessage = True # If the bot should send "Gathering Messages". Disabling this makes gathering messages faster.
sendReminders = True; # Sends reminders at intervals like 10 seconds (e.x "10 Seconds Left!")
# -------- Actual code -----------
import discord
import json;
import math;
import threading
from discord.ext import tasks
from discord import *
import random;
from discord.ext import commands
from discord.ext import *
from discord.ext.commands import *
from discord import Message
import time 
import asyncio
import io
import re
# Set-up; declares intents & global vars.
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
currentGuilds = {} # Dictionary of all guilds that have this bot.
debugMsgID = 0 # If true, rigs it so it'll always select 1 message. (This means that it also doesn't go through the filtering process for pings.)
# Checks if a message if valid (If it's not empty, if it isn't by a bot, and if it follows the servers' rules regarding attachments.)
def isValidMsg(msg : Message, g):
    if (len(msg.content) == 0): 
        return False;
    if (msg.author.bot):
        return False;
    if (msg.attachments.__len__() != 0 and not g.includeAttachments): 
        return False;
    return True;
async def convertAttachment(att : Attachment):
    return await att.to_file();
# Parses keyword arguments into a dictionary (formatted as argument=value -> dict["argument"] = value)
def parsekwargs(*args):
    toReturn = {}
    for i in args[0]:
        if "=" in i:
            k,v = i.split("=", 1)
            toReturn[k] = v
    return toReturn;
# Changes a ping to a user name
def changePing(match):
    id = match.group(1)
    bot.fetch_user(id)
    return f"[{id}]"
# Returns a string formatted as ■■■■■■■■■□□□□□□
def meter(num, amt, barAmt):
    if (amt == 0): return (barAmt*"□")
    percent = num/amt;
    # e.x 0000------ = 40%; % * barAmt = filled bars
    toReturn = (int(barAmt*percent)) * progFilled # e.x 96/108 w/ 25 bars: 0.88*25 -> 22
    toReturn += int(barAmt*(1-percent)) * progNotFilled # e.x 96/108 w/ 25 bars: 0.12*25 -> 3
    return toReturn
# Basic class for storing messages w/o all the other discord.py stuff.
class msgLike: 
    def __init__(self, content, author, id, embeds, attachments):
        self.content = content;
        self.author = author;
        self.id = id;
        self.embeds = embeds;
        self.attachments = attachments;
# Data container for servers' games.
class game:
    
    def __init__(self, id, channel, ctx):
        self.id = id;
        self.messages = [];
        self.channel = channel;
        self.ctx = ctx;
        self.targettedMessage = None;
        self.guesses = {};
        self.active = False;
        # Server settings
        self.lb = {}
        self.guessingTime = defaultGuessingTime;
        self.pingsOnly = defaultPingsOnly;
        self.msgLimit = defaultmsgLimit;
        self.includeAttachments = defaultIncludeAttachments;
        self.maxGuesses = defaultMaxGuesses;
        self.msgPing = defaultMsgPing;
    # Converts a game instance to a dictionary for saving later.
    def toDictionary(self):
        return {
            "id": self.id,
            "lb": self.lb,
            "guessingTime": self.guessingTime,
            "pingsOnly": self.pingsOnly,
            "msgLimit": self.msgLimit,
            "includeAttachments": self.includeAttachments,
            "maxGuesses": self.maxGuesses,
            "msgPing": self.msgPing
        };
    # Finds however many messages are in the guild's total history. Skips commands, and if it's larger than the msg limit, it breaks early.
    async def sumHistory(self, guild: Guild):
        sum = 0;
        for channel in guild.text_channels:
            async for message in channel.history(limit=None):
                if (message.content.startswith("?")): continue;
                if (not isValidMsg(message, self)): continue;
                sum += 1;
                if (sum >= self.msgLimit): return sum;
        return sum
    # Gathers all valid messages. If the bot settings allows it, also displays a progress bar & a counter.
    async def gatherMessages(self, guild : Guild, ctx):
        # Sends the message saying "Gathering messages 0/100 (■■■■■■■■■□□□□□□)" if bot settings allow.
        barAmt = loadingBarAmt
        msg = None
        meterStr = ""
        progStr = ""
        if (haveProgressBar): meterStr = f"({meter(0, self.msgLimit, barAmt)})"
        if (haveProgressMessage): progStr = f"0/{self.msgLimit}"
        if (haveGatheringMessage): msg = await ctx.send(f"Gathering messages; {progStr} {meterStr}")
        sum = await self.sumHistory(guild)
        if (sum >= self.msgLimit): sum = self.msgLimit;
        if (haveProgressBar): meterStr = f"({meter(0, self.msgLimit, barAmt)})";
        if (haveProgressMessage): progStr = f"0/{sum}"
        m = f"Gathering messages; {progStr} {meterStr}"
        if (msg is not None): await msg.edit(content=m)
        c = 0;
        # Clears messages, then iterates through the servers history. For each channel, it reads each message, edits it to fit the msgPing rule, then appends it to self.message.
        # If there's enough messages, then breaks early.
        self.messages = [];
        for channel in guild.text_channels:
            async for message in channel.history(limit=None):
                if not (isValidMsg(message, self)): continue;
                c += 1;
                if (c > self.msgLimit): return;
                editedContent = message.content;
                if (self.msgPing == 0):
                    editedContent = re.sub(r'@\<.*?\>', '[PING]', editedContent)
                if (self.msgPing == 1): 
                    editedContent = message.content.replace("@", "\\@")
                if (self.msgPing == 2):
                    editedContent = re.sub('\<(.*?)\>', changePing, editedContent);
                self.messages += [msgLike(editedContent, message.author, message.id, message.embeds, message.attachments)];
                if (c % math.floor(sum/barAmt) == 0 and (haveProgressBar or haveProgressMessage) and haveGatheringMessage):
                    if (haveProgressBar): meterStr = f"({meter(c, sum, barAmt)})"
                    if (haveProgressMessage): progStr = f"({len(self.messages)}/{sum})"
                    m = f"Gathering messages; {progStr} {meterStr}"
                    await msg.edit(content=m)
    # Starts a game.
    async def startGame(self):
        # Clears previous-game data, and selects a new message, then sends that message & any attachments it has.
        self.targettedMessage = random.choice(self.messages);
        self.guesses = {}
        if (debugMsgID != 0):
            self.targettedMessage = await self.channel.fetch_message(debugMsgID)
        self.active = True;
        embeds = self.targettedMessage.embeds
        if (not self.includeAttachments or len(embeds) == 0): embeds = []
        files = self.targettedMessage.attachments
        if (not self.includeAttachments or len(files) == 0): files = [];
        filesToSend = []
        if (files is not None):
            for file in files:
                attf = await convertAttachment(file)
                filesToSend += [attf]
        if (len(filesToSend) == 0): filesToSend = [];
        fstr = ";Attached files:" if len(filesToSend) > 0 else ""
        await self.ctx.send(f"Who sent; Time Left: {self.guessingTime} \"{self.targettedMessage.content}\" {fstr}")
        if (len(filesToSend) != 0 and self.includeAttachments): await self.ctx.send(files=filesToSend)
        # Counts down from the guessing time to zero, giving time for players to guess.
        for i in range(self.guessingTime, 0, -1):
            if (i % 10 == 0 or i == self.guessingTime/2 and sendReminders):
                await self.ctx.send(f"{i} Seconds left!");
            await asyncio.sleep(1)
        # Sends the winning message in the format of:
        # Message Author: @<ID> (username)
        # Winners:
        # @<Winner A ID> (Winner Name A)
        # @<Winner B ID> (Winner Name B)
        # Losers:
        # @<Loser A ID> (Loser Name A) Guessed ID (Username)
        # @<Loser B ID> (Loser Name B) Guessed ID (Username)
        
        # In addition, also modifies the leaderboard to increment winners.
        finalMsg = f"Message Author: \\@<{self.targettedMessage.author.id}> ({self.targettedMessage.author.name})\n";
        winnersMsg = f"Winners: \n"
        losersMsg = f"Losers: \n"
        for playerID, guess in self.guesses.items():
            userName = await bot.fetch_user(playerID);
            if (guess[0] == self.targettedMessage.author.id): 
                winnersMsg += f"\\@<{playerID}> ({userName})\n"
            if (playerID in self.lb):
                self.lb[playerID] += 1
            else:
                self.lb[playerID] = 1
        for playerID, guess in self.guesses.items():
            userName = await bot.fetch_user(playerID);
            guessName = await bot.fetch_user(guess[0]);
            if (guess[0] != self.targettedMessage.author.id): losersMsg += f"\\@<{playerID}> ({userName}); Guessed {guess[0]} ({guessName})\n"
        await self.ctx.send(finalMsg+winnersMsg + losersMsg)
        # Resets things for next game.
        self.active = False;
        self.targettedMessage = None;
        self.guesses = {}

bot = commands.Bot(command_prefix=cmdPrefix, description="", intents=intents) # Declares the bot (obviously)
@bot.event
async def on_ready():
    assert bot.user is not None
    print(f'\033[1;33m Logged in as {bot.user} (ID: {bot.user.id})')
# ?close - Closes the bot if ran by an admin
@bot.command(name="close")
async def close(ctx : Context):
    if (ctx.author.name != adminUser): return;
    bot.close()
    exit()
# ?start - Starts a round.
@bot.command(name="start")
async def startRound(ctx : Context):
    guild = ctx.guild
    # If guild.id isn't in currentGuilds, then initializes it into currentGuilds[guild.id]
    if (not (guild.id in currentGuilds)): 
        currentGuilds[guild.id] = game(guild.id, ctx.channel, ctx);
        print(currentGuilds[guild.id].active)
    # Makes sure that there isn't a round already going on, and initializes cg[id].channel & .ctx.
    if (guild.id in currentGuilds):
        if (currentGuilds[guild.id].active):
            await ctx.send("Round is currently ongoing. Use ?guess to guess in that round.")
            return;
        if (currentGuilds[guild.id].channel is None):
            currentGuilds[guild.id].channel = ctx.channel
        if (currentGuilds[guild.id].ctx is None):
            currentGuilds[guild.id].ctx = ctx;
    # If there's not a specific amount of messages, gather messages again.
    if (len(currentGuilds[guild.id].messages) != currentGuilds[guild.id].msgLimit): await currentGuilds[guild.id].gatherMessages(ctx.guild, ctx);
    # If no game is happening already, then start one.
    if (currentGuilds[guild.id].active == False):
        await currentGuilds[guild.id].startGame();
# ?guess str - Makes a guess in a round.
@bot.command(name="guess")
async def guess(ctx : Context, g1 : str):
    guild = ctx.guild
    guess = g1;
    if (guild.id in currentGuilds):
        g = currentGuilds[guild.id]
        guessProfile = None;
        # If the sender hasn't guessed yet, set g.guesses to [0,0]. These arrays are in the format of [id, guessAmt]
        if (not ctx.author.id in g.guesses): 
            g.guesses[ctx.author.id] = [0,0]
            guessProfile = g.guesses[ctx.author.id]
        else:
            guessProfile = g.guesses[ctx.author.id]
        if (guessProfile is not None):
            # if the guesser has guessed too many times, then don't let them guess again.
            if (guessProfile[1] >= g.maxGuesses): 
                await ctx.reply("Max guesses have been reached."); 
                return;
            # Short-cut for guessing yourself.
            if (guess == "!Self"):
                g.guesses[ctx.author.id][0] = ctx.author.id;
                g.guesses[ctx.author.id][1] += 1;
            # Parses pings.
            elif (guess.startswith("<@")):
                # @<id>
                substr = guess[2:guess.__len__()-2]
                print(substr)
                g.guesses[ctx.author.id][1] += 1;
                g.guesses[ctx.author.id][0] = substr;
            # Parses escape-pings.
            elif (guess.startswith("\\@")):
                # \\@<id>
                substr = guess[2:guess.__len__()-2]
                print(substr)
                g.guesses[ctx.author.id][1] += 1;
                g.guesses[ctx.author.id][0] = substr;
            else: 
                # Parses usernames
                for member in guild.members:
                    if (guess == member.name and g.pingsOnly is False):
                        g.guesses[ctx.author.id][0] = member.id;
                        g.guesses[ctx.author.id][1] += 1;
                        return;
                    elif (guess == member.name):
                        await ctx.send("pingsOnly is enabled. You have to use either pings or escape char pings. (@) or (\\@)")
                        return;
                # nickname or display name (Not allowed, ever)
                for member in guild.members:
                    if (guess == member.nick or guess == member.display_name):
                        await ctx.send("Nicknames and display names are invalid. use ?guessFormats to see valid formatting for guesses.")
        else:
            await ctx.send("You have already guessed. Wait until the round is over to guess again.");
    else:
        await ctx.send("There's no current round started. Use ?start to start a round.")
# ?guessFormats - Sends valid guess formats
@bot.command(name="guessFormats")
async def guessFormats(ctx):
    await ctx.send("""
Valid formats for guessing:
- \\\\@<id> - Escape Char Pinging - Developer mode must be on, and you have to copy their User ID by right clicking their name and clicking "Copy User ID". Use if you don't actually want to ping a person. e.x \\@<438360707671523328>
- @ - Pinging e.x "@namehere_numbershere"
- !Self - Guess yourself\n
Sometimes valid:
- "Username" - Self explanatory; has to be in quotes. e.x "namehere_numbershere"; server configures if this is valid for guesses.\n
NOT valid formats for guessing:
- Nicknames
- Display names
    
Generally, it's better to do Escape char pinging or normal pinging, as oftentimes there's people w/ same usernames.
""")
# Checks if a string is a valid bool input.
async def validBoolInput(str, ctx):
    if (str == "1" or str == "0"):
        return True 
    await ctx.send("Invalid boolean input. All bool inputs have to be either 1 or 0.")
    return False 
# Checks if a entered input is a valid number.
async def validNumberInput(num, min, max, ctx):
    if (num >= min and num <= max): return True;
    if (num == None): return True;
    await ctx.send(f"Invalid number input {num}; has to be between {min} and {max} inclusive");
    return False; 
# ?rules - Changes rules; only owner of a server can do this. If no arguments are passed through, lists the current rules.
@bot.command(name="rules")
async def rules(ctx : Context, *args):
    kwargs = parsekwargs(args)
    if (not ctx.guild.id in currentGuilds):
        currentGuilds[ctx.guild.id] = game(ctx.guild.id, ctx.channel, ctx)
    else:
        if (currentGuilds[ctx.guild.id].channel is None): currentGuilds[ctx.guild.id].channel = ctx.channel;
        if (currentGuilds[ctx.guild.id].ctx is None): currentGuilds[ctx.guild.id].ctx = ctx;
    warningTxt = ""
    if (kwargs != {} and ctx.author.id == ctx.guild.owner_id):
        warningTxt = "You do not have permission to modify msgguessr rules. \n"
    if ("time" in kwargs and ctx.author.id == ctx.guild.owner_id):
        v = await validNumberInput(int(kwargs["time"]), 5, 600, ctx)
        if (v): currentGuilds[ctx.guild.id].guessingTime = int(kwargs["time"])
    if "pingsOnly" in kwargs and ctx.author.id == ctx.guild.owner_id:
        v = await validBoolInput((kwargs["pingsOnly"]), ctx)
        if (v): currentGuilds[ctx.guild.id].pingsOnly = bool(kwargs["pingsOnly"])
    if "msgLimit" in kwargs and ctx.author.id == ctx.guild.owner_id:
        v = await validNumberInput(int(kwargs["msgLimit"]), 100, 10000, ctx)
        if (v): currentGuilds[ctx.guild.id].msgLimit = int(kwargs["msgLimit"])
    if "includeAttachments" in kwargs and ctx.author.id == ctx.guild.owner_id:
        v = await validBoolInput((kwargs["includeAttachments"]), ctx)
        if (v): currentGuilds[ctx.guild.id].includeAttachments = bool(kwargs["includeAttachments"])
    if "maxGuesses" in kwargs and ctx.author.id == ctx.guild.owner_id:
        v = await validNumberInput(int(kwargs["maxGuesses"]), 1, 20, ctx)
        if (v): currentGuilds[ctx.guild.id].maxGuesses = int(kwargs["maxGuesses"])
    if "msgPing" in kwargs and ctx.author.id == ctx.guild.owner_id:
        v = await validNumberInput(int(kwargs["msgPing"]), 0, 2, ctx)
        if (v): currentGuilds[ctx.guild.id].msgPing = int(kwargs["msgPing"])
    await ctx.send(warningTxt + f"""
Rules:
Time - {currentGuilds[ctx.guild.id].guessingTime}
pingsOnly - {currentGuilds[ctx.guild.id].pingsOnly}
msgLimit - {currentGuilds[ctx.guild.id].msgLimit}
includeAttachments - {currentGuilds[ctx.guild.id].includeAttachments}
maxGuesses - {currentGuilds[ctx.guild.id].maxGuesses}
msgPing - {currentGuilds[ctx.guild.id].msgPing}
""")
# ?cmds - Lists all commands. Args can be passed through to get specification on some commands.
@bot.command(name="cmds")
async def help(ctx : Context, *args):
    if "rules" in args:
        await ctx.send("""
time= - Amount of time people have to guess (In seconds)
pingsonly= - Only allow pings or escape-char pings for guesses. (1 or 0)
msgLimit= - Amount of messages that are viable for guesses. Set to None for the bot to take all messages sent in server. (integer)
includeAttachments= - Include other attachments (Still includes images, though). (1 or 0)
maxGuesses= - Allow users to change their guess up to maxGuesses times. (integer)
msgPing = Include pings inside of messages to guess. If 0, deletes the ping entirely, replacing it with [PING]. If 1, replaces the ping with an escapechar ping. If 2, replaces ping with persons' username. If 3, doesn't modify the ping at all.
      
Usage example:
?rules time=65 pingsonly=1 includeAttachments=1
""")
        pass;
    if "guessFormats" in args:
        await guessFormats(ctx)
    if (len(args) == 0):
        await ctx.send("""
Bot commands: \n
?cmds - See a list of commands
?lb - Leaderboard
?rules - Change game rules such as guessing time, msg limit, multiple guesses, etc.
?start - Start a round
?guess - Guess a person who sent it.
                 
You can use ?cmds cmd to gain more clarification about parameters.
 """)
# Lists the leaderboard for the server.
@bot.command(name="lb")
async def lb(ctx : Context):
    if (ctx.guild.id in currentGuilds):
        toSend = f"Leaderboard: \n"
        lb = currentGuilds[ctx.guild.id].lb;
        s = dict(sorted(lb.items(), key=lambda item: item[1], reverse=True))
        c = 1
        for key,val in s.items():
            user = await bot.fetch_user(key)
            toSend += f"{c}. {user} - {val}\n"
            c += 1;
        await ctx.send(toSend)
# Converts currentGuilds to a dictionary for later Jsonification.
def convertAllServers():
    toReturn = {};
    for key,val in currentGuilds.items():
        toReturn[key] = val.toDictionary();
    return toReturn;
# saves data
def save():
    if (saveFile == ""): return;
    with open(saveFile, "w") as file:
        json.dump(convertAllServers(), file)
    print("\033[0;32m Saved data")
# ?saveAll - saves data
@bot.command(name="saveAll")
async def saveCmd(ctx : Context):
    if (ctx.author.name == adminUser):
        save()
# Parses Json into a game class.
def parseJson(val):
    toReturn = game(val["id"], None, None);
    toReturn.id = val["id"];
    toReturn.lb = val["lb"];
    toReturn.guessingTime = val["guessingTime"]
    toReturn.pingsOnly = val["pingsOnly"]
    toReturn.msgLimit = val["msgLimit"]
    toReturn.includeAttachments = val["includeAttachments"]
    toReturn.maxGuesses = val["maxGuesses"]
    toReturn.msgPing = val["msgPing"]
    return toReturn;
# Loads data
def loadData():
    if (saveFile == ""): return;
    data = "";
    with open(saveFile, "r") as file:
        data = file.read()
    jsonData = json.loads(data)
    for key,val in jsonData.items():
        currentGuilds[int(key)] = parseJson(val)
try:
    loadData()
    print('\033[0;32m Loaded data.')
    if (saveFile != ""):
        saveTimer = threading.Timer(saveInterval, save)
        saveTimer.start()
        print('\033[0;32m Started saving timer.')
except Exception as e:
    print(f"\033[0;31m Error occurred in loading data {e}")
finally:
    print("\033[0;32m Starting bot")
    bot.run(token=token)

