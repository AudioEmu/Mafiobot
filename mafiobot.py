import discord #imports discord.py, includes everything needed here except for interaction commands
from discord import app_commands #includes interaction commands
import os #used to check if saved files exist, but primarily is used for os.linesep on fstrings
import pickle #used to save and load objects like the player list, player channels, and game state. Importantly, pickle is not secure enough to be trusted with external objects. Only import things the bot makes

from mafiobotClasses import gameState #imports the gameState object that tracks day/night and day channel
from mafiobotClasses import player #imports the player object assigned to each player
#^-----importing necessary packages-----^

#v----- FUNCTION DEFINITIONS -----v
#Defining often used functions up here to make further code easier to read and write:
def pSave(objectToSave, fileName): #Use pickle to dump object into fileName
	with open(fileName, 'wb') as f:
		pickle.dump(objectToSave, f)
def pLoad(fileName): #Use pickle to load fileName into object
	with open(fileName, 'rb') as f:
		loadedObject = pickle.load(f)
		return loadedObject

#v-----VARIABLE DEFINITIONS-----v
#Server and Role IDs for the bot to reference later
#These need to be changed to match whatever server you want to run the bot on
serverID=1087918199972053004
gmRoleID=1091835818475270164
deadRoleID=1088273637838176317
playingRoleID=1088273694150901830
#The channel that the bot prints output and logs to
logChannelID=1091826274630107227
#fileNames for saved objects
playersSaveFile="players.pickle"
stateSaveFile="state.pickle"
playerChannelsFile="playerChannels.pickle"
#The token that tells the program which bot it is
botToken='Revoked so that you nerds can\'t steal my bot'
#telling the program to monitor all possible intents. Definitely not needed, will probably reign this in later
intent=discord.Intents.all()

#Create an object that represents the bot
client = discord.Client(intents=intent)

#Look for previously saved gameStates, player lists, and player channel assignments. If found, load them. If not, keep a default or empty version
state=gameState()
print(f'Looking for saved game state data at stateSaveFile')
if os.path.isfile(stateSaveFile):
	print(f'Saved game state found. Loading it into state object')
	state=pLoad(stateSaveFile)
	print(f'Loaded!')
else:
	print(f'File not found! Starting at night 0 with default state, and saving to stateSaveFile...')
	pSave(state, stateSaveFile)
	print(f'Saved!')

players=[]
print(f'Looking for saved players at playersSaveFile')
if os.path.isfile(playersSaveFile):
	print(f'Player list save data found! Loading it to players list:')
	players=pLoad(playersSaveFile)
	print(f'Loaded!')
else:
	print(f'Players file not found! Use !initPlayers to populate this empty one!')

playerChannels = {}
print(f'Looking for player channels saved at playerChannelsFile:')
if os.path.isfile(playerChannelsFile):
	print(f'Player Channel data found! Loading now!')
	playerChannels=pLoad(playerChannelsFile)
	print(f'Loaded!')
else:
	print(f'No saved dict of player channels found! please use /assign_player_channel to populate this dict')

#Create a tree full of all slash and context commands
tree=app_commands.CommandTree(client)

##################################################
#####             SLASH COMMANDS             #####
##################################################

@tree.command(
	name='view_day_info',
	description='See current day/night phase and count',
	guild=discord.Object(id=serverID)
			)
async def viewDayInfo(interaction):
	global state
	await interaction.response.send_message(f'It is {state.returnDayState()}!', ephemeral=True)

@tree.command(
	name='view_players',
	description='Get a list of currently registered players.',
	guild=discord.Object(id=serverID)
			)
async def viewPlayers(interaction):
	listString=f'The current players are:{os.linesep}'
	for p in players:
		listString+=f'{p.displayName}{os.linesep}'
	await interaction.response.send_message(listString, ephemeral=True)

@tree.command(
	name='view_player_info',
	description='See status of selected player. Can only be used on yourself if you\'re not GM',
	guild=discord.Object(id=serverID)
				)
async def viewPlayer(interaction, target :discord.Member):
	isAllowed=False
	foundPlayer=False
	playerIndex=None
	global players
	for role in interaction.user.roles:
		if (role.id==gmRoleID or interaction.user.id==target.id):
			isAllowed=True
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundPlayer=True
			playerIndex=i
	if not isAllowed:
		await interaction.response.send_message('Only GMs can use this command on other people!', ephemeral=True)
	elif not foundPlayer:
		await interaction.response.send_message('This person is not in the list of active players!', ephemeral=True)
	else:
		tempPlayer=players[playerIndex] #v----- There's gotta be an easier way to make this line lol
		await interaction.response.send_message(f'{target.display_name}:{os.linesep}ID:{tempPlayer.memID}{os.linesep}Comments Remaining:{tempPlayer.commentsRemaining}{os.linesep}Can Overhear:{tempPlayer.canOverhear}{os.linesep}Can Michael Shot:{tempPlayer.canVigShot}{os.linesep}Can Call A Meeting: {tempPlayer.canCallMeeting}{os.linesep}Parlay Ammo:{tempPlayer.parlayAmmo}', ephemeral=True)


@tree.command(
	name='call_meeting',
	description='Call emergency meeting if you\'re crewmate',
	guild=discord.Object(id=serverID)
			)
async def callMeeting(interaction, message :str=None):
	global players
	global state
	foundPlayer=False
	isDead=False
	isAble=False
	for i, player in enumerate(players):
		if player.memID==interaction.user.id:
			meetingCallerIndex=i
			foundPlayer=True
			isAble = player.canCallMeeting
			for role in interaction.user.roles:
				if role.id==deadRoleID:
					isDead=True
	if isDead:
		await interaction.response.send_message(f'You must be alive to call an emergency meeting!', ephemeral=True)
	elif not isAble:
		await interaction.response.send_message(f'Your role is not able to call meetings!', ephemeral=True)
	elif not state.isDay:
		await interaction.response.send_message(f'You can only call a meeting during the day!', ephemeral=True)
	elif not foundPlayer:
		await interaction.response.send_message(f'You are not in the list of active players!', ephemeral=True)
	else:
		await dayChannel.set_permissions(interaction.guild.default_role, send_messages=False)
		state.advancePhase()
		embed=discord.Embed(
			title=f'***I\'VE CALLED AN EMERGENCY MEETING***',
			description=f'{message}{os.linesep}It is now {state.returnDayState()}!{os.linesep}<@&{playingRoleID}>',
			color=discord.Colour.red()
						)
		embed.set_author(
			name='Crewmate',
			icon_url='https://impostor.rl.run/static/media/impostor.4b5e387e.png'
						)
		await dayChannel.send(f'', embed=embed)
		players[meetingCallerIndex].canCallMeeting=False
		pSave(state, stateSaveFile)
		pSave(players, playersSaveFile)
		await interaction.response.send_message(f'You successsfully called a meeting!', ephemeral=True)

@tree.command(
	name="set_player_channel",
	description="GMs use this to assign people their player channels",
	guild=discord.Object(id=serverID)
			)
async def setPlayerChannel(interaction, target_player :discord.Member, target_channel_id :str):
	global playerChannels
	isAllowed=False
	for role in interaction.user.roles:
		if role.id==gmRoleID:
			isAllowed=True
	if not isAllowed:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	else:
		targetChannel=client.get_channel(int(target_channel_id))
		try:
			testVar=(f'{targetChannel.name}')
		except:
			await interaction.response.send_message(f'Could not find a channel with that name!', ephemeral=True)
		else:
			playerChannels.update({str(target_player.id) : targetChannel.id})
			await targetChannel.send(f'This channel has been designated {target_player.mention}\'s player channel!')
			await interaction.response.send_message(f'Done! Saving playerChannels to file', ephemeral=True)
			pSave(playerChannels, playerChannelsFile)
@tree.command(
	name='comment',
	description='Leave a comment in another player\'s player channel',
	guild=discord.Object(id=serverID)
			)
async def comment(interaction, recipient :discord.Member, anon :bool=True, message :str=None, attachment :discord.Attachment=None):
	global players
	global playerChannels
	global state
	foundSender=False
	senderHasComments=False
	senderPlayerChannel=None
	senderIndex=None
	foundRecipient=False
	recipientIndex=None
	recipientPlayerChannel=None
	wasOverheard=False
	overheardIn=None
	if anon:
		sender="Anon"
	else:
		sender=interaction.user.display_name
	for i, player in enumerate(players):
		if player.memID==interaction.user.id:
			foundSender=True
			senderIndex=i
			if player.commentsRemaining>0:
				senderHasComments=True
			if str(player.memID) in playerChannels:
				senderPlayerChannel=client.get_channel(playerChannels[str(player.memID)])
		if player.memID==recipient.id:
			foundRecipient=True
			recipientIndex=i
			if str(player.memID) in playerChannels:
				recipientPlayerChannel=client.get_channel(playerChannels[str(player.memID)])
	for i, player in enumerate(players):
		if(player.canOverhear and (not i==senderIndex) and (not i==recipientIndex)):
			if str(player.memID) in playerChannels:
				wasOverheard=True
				overheardIn=client.get_channel(playerChannels[str(player.memID)])
	if not (state.isDay or state.phaseNumber==1):
		await interaction.response.send_message(f'You can only send comments during the day or night 1!', ephemeral=True)
	elif not foundSender:
		await interaction.response.send_message(f'You are not in the list of active players!', ephemeral=True)
	elif not foundRecipient:
		await interaction.response.send_message(f'Your target is not in the list of active players!', ephemeral=True)
	elif not senderHasComments:
		await interaction.response.send_message(f'You are out of comments!', ephemeral=True)
	elif recipientPlayerChannel==None:
		await interaction.response.send_message(f'Your recipient doesn\'t have a player cannel! Have a gm use /set_player_channel to give them one!', ephemeral=True)
	elif senderPlayerChannel==None:
		await interaction.response.send_message(f'You don\'t have a player channel! Have a GM use /set_player_channel to give you one!', ephemeral=True)
	else:
		outboundEmbed=discord.Embed(
			title=f'**A Message!:**',
			description=f'{message}',
			color=discord.Colour.blue()
									)
		loggedEmbed=discord.Embed(
			title=f'**You commented {players[recipientIndex].displayName}**',
			description=f'{message}',
			color=discord.Colour.green()
									)
		overheardEmbed=discord.Embed(
			title=f'**You overhead a comment:**',
			description=f'{message}',
			color=discord.Colour.red()
									)

		if not attachment==None:
			outboundEmbed.set_image(url=attachment.url)
			loggedEmbed.set_image(url=attachment.url)
			overheardEmbed.set_image(url=attachment.url)

		if not anon:
			outboundEmbed.set_author(name=f'{sender}', icon_url=interaction.user.avatar.url)
		else:
			outboundEmbed.set_author(name=f'{sender}', icon_url='https://creazilla-store.fra1.digitaloceanspaces.com/emojis/44265/disguised-face-emoji-clipart-md.png')

		await recipientPlayerChannel.send(f'', embed=outboundEmbed)
		await senderPlayerChannel.send(f'', embed=loggedEmbed)
		if wasOverheard:
			await overheardIn.send(f'', embed=overheardEmbed)
		players[senderIndex].commentsRemaining-=1
		await interaction.response.send_message(f'Sent! You have {players[senderIndex].commentsRemaining} comments remaining!', ephemeral=True)
		pSave(players, playersSaveFile)

@tree.command(
	name='parlay',
	description='Deliver a faked comment using the Hunger\'s Parlay ability',
	guild=discord.Object(id=serverID)
			)
async def parlay(interaction, recipient :discord.Member, disguise :discord.Member, anon :bool=False, message :str=None, attachment :discord.Attachment=None):
	global players
	global playerChannels
	global state
	foundSender=False
	senderHasComments=False
	senderPlayerChannel=None
	senderIndex=None
	foundRecipient=False
	recipientIndex=None
	recipientPlayerChannel=None
	wasOverheard=False
	overheardIn=None
	if anon:
		sender="Anon"
	else:
		sender=disguise.display_name
	for i, player in enumerate(players):
		if player.memID==interaction.user.id:
			foundSender=True
			senderIndex=i
			if player.parlayAmmo>0:
				senderHasComments=True
			if str(player.memID) in playerChannels:
				senderPlayerChannel=client.get_channel(playerChannels[str(player.memID)])
		if player.memID==recipient.id:
			foundRecipient=True
			recipientIndex=i
			if str(player.memID) in playerChannels:
				recipientPlayerChannel=client.get_channel(playerChannels[str(player.memID)])
	for i, player in enumerate(players):
		if(player.canOverhear and (not i==senderIndex) and (not i==recipientIndex)):
			if str(player.memID) in playerChannels:
				wasOverheard=True
				overheardIn=client.get_channel(playerChannels[str(player.memID)])
	if not (state.isDay or state.phaseNumber==1):
		await interaction.response.send_message(f'You can only send comments during the day or night 1!', ephemeral=True)
	elif not foundSender:
		await interaction.response.send_message(f'You are not in the list of active players!', ephemeral=True)
	elif not foundRecipient:
		await interaction.response.send_message(f'Your target is not in the list of active players!', ephemeral=True)
	elif not senderHasComments:
		await interaction.response.send_message(f'You are out of Parlay ammo!', ephemeral=True)
	elif recipientPlayerChannel==None:
		await interaction.response.send_message(f'Your recipient doesn\'t have a player cannel! Have a gm use /set_player_channel to give them one!', ephemeral=True)
	elif senderPlayerChannel==None:
		await interaction.response.send_message(f'You don\'t have a player channel! Have a GM use /set_player_channel to give you one!', ephemeral=True)
	else:
		outboundEmbed=discord.Embed(
			title=f'**A Message!:**',
			description=f'{message}',
			color=discord.Colour.blue()
									)
		loggedEmbed=discord.Embed(
			title=f'**You Parlayed with {recipient.display_name} while disguised as {sender}**',
			description=f'{message}',
			color=discord.Colour.green()
									)
		overheardEmbed=discord.Embed(
			title=f'**You overhead a comment:**',
			description=f'{message}',
			color=discord.Colour.red()
									)

		if not attachment==None:
			outboundEmbed.set_image(url=attachment.url)
			loggedEmbed.set_image(url=attachment.url)
			overheardEmbed.set_image(url=attachment.url)
		if not anon:
			outboundEmbed.set_author(name=f'{sender}', icon_url=disguise.avatar.url)
		else:
			outboundEmbed.set_author(name=f'{sender}', icon_url='https://creazilla-store.fra1.digitaloceanspaces.com/emojis/44265/disguised-face-emoji-clipart-md.png')

		await recipientPlayerChannel.send(f'', embed=outboundEmbed)
		await senderPlayerChannel.send(f'', embed=loggedEmbed)
		if wasOverheard:
			await overheardIn.send(f'', embed=overheardEmbed)
		players[senderIndex].parlayAmmo-=1
		await interaction.response.send_message(f'Sent! You have {players[senderIndex].parlayAmmo} Parlays remaining!', ephemeral=True)
		pSave(players, playersSaveFile)
#################################################
#####            CONTEXT COMMANDS           #####
#################################################
@tree.context_menu(
	name='Set as day channel',
	guild=discord.Object(id=serverID)
				)
async def setDayChannel(interaction, target :discord.Message):
	global state
	global dayChannel
	state.dayChannelID=target.channel.id
	dayChannel=client.get_channel(state.dayChannelID)
	pSave(state, stateSaveFile)
	await interaction.response.send_message(f'Day channel set to {dayChannel.name}!', ephemeral=True)

@tree.context_menu(
	name='Shoot This Player',
	guild=discord.Object(id=serverID)
				)
async def vigShot(interaction, target :discord.Member):
	global players
	global state
	foundShooter=False
	foundTarget=False
	shooterIndex=None
	targetIndex=None
	shooterDead=False
	targetDead=False
	shooterHasAmmo=False

	for role in interaction.user.roles:
		if role.id==deadRoleID:
			shooterDead=True
	for role in target.roles:
		if role.id==deadRoleID:
			targetDead=True
	for i, player in enumerate(players):
		if(player.memID==interaction.user.id):
			shooterIndex=i
			foundShooter=True
			shooterHasAmmo=player.canVigShot
		if(player.memID==target.id):
			foundTarget=True
			targetIndex=i
	
	if not foundShooter:
		await interaction.response.send_message(f'You are not in the list of active players!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'Your target is not in the list of active players!', ephemeral=True)
	elif not shooterHasAmmo:
		await interaction.response.send_message(f'You don\'t have ammo for that!', ephemeral=True)
	elif shooterDead:
		await interaction.response.send_message(f'You can\'t shoot while dead!', ephemeral=True)
	elif targetDead:
		await interaction.response.send_message(f'You can\'t shoot dead people!', ephemeral=True)
	elif state.phaseNumber<=1:
		await interaction.response.send_message(f'You can\'t shoot until Day 2!', ephemeral=True)
	elif not state.isDay:
		await interaction.response.send_message(f'You can only shoot during the day!', ephemeral=True)
	else:
		await dayChannel.set_permissions(interaction.guild.default_role, send_messages=False)
		state.advancePhase()
		embed=discord.Embed(
			title=f'***BANG***',
			description=f'{interaction.user.display_name} has shot {target.display_name} to death!{os.linesep}It is {state.returnDayState()}!{os.linesep}<@&{playingRoleID}>',
			color=discord.Colour.blue()
							)
		embed.set_author(
			name="Michael",
			icon_url="https://smtd.umich.edu/wp-content/uploads/2022/06/mcelroy-crop.png"
						)
		await dayChannel.send(f'', embed=embed)

		players[shooterIndex].canVigShot=False
		deadRole=discord.utils.get(interaction.guild.roles, id=deadRoleID)
		await target.add_roles(deadRole)
		pSave(players, playersSaveFile)
		pSave(state, stateSaveFile)
		await interaction.response.send_message(f'You successfully shot your target!', ephemeral=True)




#v----- TOGGLERS -----v
@tree.context_menu(
	name="Toggle Meetings",
	guild=discord.Object(id=serverID)
				)
async def toggleCanMeeting(interaction, target :discord.Member):
	isAllowed=False
	foundTarget=False
	targetIndex=None
	global players
	for role in interaction.user.roles:
		if role.id==gmRoleID:
			isAllowed=True
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not isAllowed:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'The chosen member is not in the list of active players!', ephemeral=True)
	else:
		if players[targetIndex].canCallMeeting:
			players[targetIndex].canCallMeeting=False
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can no longer call a meeting!', ephemeral=True)
		else:
			players[targetIndex].canCallMeeting=True
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can now call a meeting!', ephemeral=True)

@tree.context_menu(
	name="Toggle Overhearing",
	guild=discord.Object(id=serverID)
				)
async def toggleOverhearing(interaction, target :discord.Member):
	isAllowed=False
	foundTarget=False
	targetIndex=None
	global players
	for role in interaction.user.roles:
		if role.id==gmRoleID:
			isAllowed=True
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not isAllowed:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'The chosen member is not in the list of active players!', ephemeral=True)
	else:
		if players[targetIndex].canOverhear:
			players[targetIndex].canOverhear=False
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can no longer overhear comments!', ephemeral=True)
		else:
			players[targetIndex].canOverhear=True
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can now overhear comments!', ephemeral=True)

@tree.context_menu(
	name="Toggle Michael Shot",
	guild=discord.Object(id=serverID)
				)
async def toggleVigShot(interaction, target :discord.Member):
	isAllowed=False
	foundTarget=False
	targetIndex=None
	global players
	for role in interaction.user.roles:
		if role.id==gmRoleID:
			isAllowed=True
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not isAllowed:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'The chosen member is not in the list of active players!', ephemeral=True)
	else:
		if players[targetIndex].canVigShot:
			players[targetIndex].canVigShot=False
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can no longer use Michael\'s Revenge!', ephemeral=True)
		else:
			players[targetIndex].canVigShot=True
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can now use Michael\'s Revenge!', ephemeral=True)

@tree.context_menu(
	name="Toggle Parlay",
	guild=discord.Object(id=serverID)
				)
async def toggleParlayAmmo(interaction, target :discord.Member):
	isAllowed=False
	foundTarget=False
	targetIndex=None
	global players
	for role in interaction.user.roles:
		if role.id==gmRoleID:
			isAllowed=True
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not isAllowed:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'The chosen member is not in the list of active players!', ephemeral=True)
	else:
		if not players[targetIndex].parlayAmmo==0:
			players[targetIndex].canVigShot=0
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can no longer use Parlay!', ephemeral=True)
		else:
			players[targetIndex].parlayAmmo=3
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} can now use Parlay {players[targetIndex].parlayAmmo} times!', ephemeral=True)

##################################################
#####             CHAT COMMANDS              #####
##################################################
@client.event
async def on_message(message):
	global players
	global state

	if(message.author==client.user):
		return

	if(message.content=='!initPlayers'):
		for role in message.author.roles:
			if role.id==gmRoleID:
				players=[]
				for member in message.guild.members:
					for role in member.roles:
						if role.id==playingRoleID:
							thisPlayer=player(f'{member.name}#{member.discriminator}', member.display_name, member.id)
							players.append(thisPlayer)
				await logChannel.send(f'Players list populated! List currently consists of:')
				outputString = ""
				for i in players:
					outputString+=f'{i.displayName}{os.linesep}'
				await logChannel.send(f'{outputString}')
				await logChannel.send(f'Saving players list to playersSaveFile')
				pSave(players, playersSaveFile)
				await logChannel.send(f'Saved!')
		await message.delete()

	if(message.content=='!viewDayChannel'):
		await logChannel.send(f'{message.author.mention}{dayChannel.name}')
		await message.delete()

	if(message.content=='!advancePhase'):
		isAllowed=False
		for role in message.author.roles:
			if role.id==gmRoleID:
				isAllowed=True
		if not isAllowed:
			await message.delete()
		else:
			oldPhaseNumber=state.phaseNumber
			state.advancePhase()
			newPhaseNumber=state.phaseNumber
			if not (newPhaseNumber==oldPhaseNumber):
				if newPhaseNumber==1:
					for p in players:
						p.commentsRemaining=99999
				else:
					for p in players:
						p.commentsRemaining=3
			pSave(players, playersSaveFile)
		pSave(state, stateSaveFile)
		await logChannel.send(f'{message.author.display_name} advanced the phase! It is now {state.returnDayState()}!')
		await message.delete()

	if(message.content=='!resetState'):
		isAllowed=False
		for role in message.author.roles:
			if role.id==gmRoleID:
				isAllowed=True
		if not isAllowed:
			await message.delete()
		else:
			state.resetState()
			await logChannel.send(f'{message.author.mention} has reset to Night 0 with no day channel!')
			pSave(state, stateSaveFile)
			await message.delete()

	if(message.content=="!toggleDay"):
		isAllowed=False
		for role in message.author.roles:
			if role.id==gmRoleID:
				isAllowed=True
		if not isAllowed:
			message.delete()
		else:
			if state.isDay:
				state.isDay=False
			else:
				state.isDay=True
			await logChannel.send(f'{message.author.mention} made it {state.returnDayState()}!')
			message.delete()


#v-----Run when bot is ready-----v
@client.event
async def on_ready():
	global logChannel
	global dayChannel
	logChannel=client.get_channel(logChannelID)
	dayChannel = client.get_channel(state.dayChannelID)
	await tree.sync(guild=discord.Object(id=serverID))


#v-----RUN IT FOR REAL-----v
client.run(botToken)