# msgGuesser
Highly customizable discord bot game
## How to play:
The basic idea is to see if you can guess who sent a discord message. When ?start is ran, it'll show a random message, and players have to guess who sent that message.
## Commands:
| Name  | Actions | Parameters | Permissions | Usage Example
| ------------- | ------------- | ------------- | ------------- | ------------- |
| ?start | Starts a round | | | ?start |
| ?guess | Makes a guess | str | | ?guess username |
| ?guessFormats | Lists valid guess formats | | | ?guessFormats | 
| ?rules | Lists current rules | | | ?rules |
| ?cmds | Lists all commands | | | ?cmds |
| ?cmds | Lists specifics of a command | str | | ?cmds rules |
| ?lb | Lists the leaderboard in a server | | | ?lb |
| ?rules | Changes rules | 1-6 | Server Owner | ?rules guessingTime=20 |
| ?close | Closes the bot | | Bot Admin | ?close |
| ?saveAll | Saves data | | Bot Admin | ?saveAll |
# Hosting Guide:
1. Make a discord bot (By going [Here](https://discord.com/developers/applications) )
2. Give it the Presence, Server Members, and Message Content intents (by going to your bot, then overview->bot)
3. Copy the token (By going to overview->bot, then clicking "Reset Token")
4. Go to overview-Installation, set the Installation Context to "Guild Install".
5. In the installation menu, set the permissions of the bot to administrator.
6. Invite it to your server.
7. Download the script in this github page.
8. Open the script in an IDE, such as Visual Studio Code.
9. On line 2, set token to be equal to your bots token.
10. If you want data to be saved, set saveFile & saveInterval (Lines 3 & 4) to whatever you want them to be.
11. Set adminUser (Line 5) to your discord username.
12. Set cmdPrefix (Line 6) to whatever you want the prefix to be. Don't choose anything that is commonly said, or conflicts with other bots.
13. Set the default settings (Lines 8-13) for new servers to whatever you want them to be; If you only have this in one server, you can manually change these yourself using ?rules.
14. Change cosmetic settings (Lines 15-21) to whatever you want.
15. Open command prompt, move over to the directory you have the bot in. Use pip install -r requirements.txt (Skip this step if you have discord.py installed already)
