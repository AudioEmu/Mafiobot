# Mafiobot
 TAZCJ Mafia Discord Bot

# SETUP

Before all else (and hopefully only once ever per player) designate each player's player channel. To do so, use /set_player_channel. This command takes two arguments: a discord member (the list of which will populate as you begin typing) and a channel ID. The channel ID can be found by right clicking the desired channel and clicking "Copy Channel ID." If successful, the channel in question will display a message tagging the user it's been assigned to.

Next, make sure all users playing (and only the users playing) have been given the Player role and do !initPlayers. This will create a player object for each player and add them all to a list called players. The exact contents of that object are viewable in mafiobotClasses.py

Run !resetState. This will ensure you are starting with the typical default mafia game setup. What exactly that entails can be viewed in mafiobotClasses.py and is also output to the log channel. Create your day 1 channel and type any message in it. Right click that message and go to apps->set as day channel. This tells the bot where to put relevant messages and what channel to lock as night falls.

Assign special traits to players. As of now this consists of:
- Michael's Revenge
- Emergency Meeting
- Hunger/Ditto overhear
- Mask name and picture

To enable the first 3, simply right click a player anywhere in the server and go to apps->toggle \*feature\*. This will provide you with an ephemeral response from the bot with the new value for that player, and can be confirmed later by using /view_player_info

If you are running a masquerade game, do !toggleMasquerade to turn on mask mode, then for each player use /set_mask. /set_mask takes three arguments: The user whos mask you are setting, a string for the name of that mask, and an uploaded attachment for that mask's PFP. You will receieve an ephemeral response with the result of that command.

# DURING THE GAME

Remember before each day phase starts to right click a message in the new day phase channel and set it as the day channel. 