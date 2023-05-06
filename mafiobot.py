import discord, os, pickle, aiohttp, pprint, asyncio
from dotenv import load_dotenv
from discord import app_commands, Webhook

from mafiobotClasses import gameState
from mafiobotClasses import player

load_dotenv() #get private or server specific vars from .env

#v----- Function Definitions-----v
def pSave(objectToSave, fileName): #Use pickle to dump object into fileName
	with open(fileName, 'wb') as f:
		pickle.dump(objectToSave, f)
def pLoad(fileName): #Use pickle to load fileName into object
	with open(fileName, 'rb') as f:
		loadedObject = pickle.load(f)
		return loadedObject

#v----- Variable Definitions -----v
serverID=int(os.getenv('serverID'))
thisServer=None
gmRole=None
deadRole=None
playingRole=None
logChannelID=int(os.getenv('logChannelID'))
playersSaveFile="players.pickle"
stateSaveFile="state.pickle"
playerChannelsFile="playerChannels.pickle"
botToken=os.getenv('botToken')
masqueradeWebhookURL=os.getenv('masqueradeWebhookURL')
raveyardWebhookURL=os.getenv('raveyardWebhookURL')
intent=discord.Intents.all()

client = discord.Client(intents=intent)

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
	await interaction.response.send_message(f'It is {state.returnDayState()}! Free Comments={state.freeComments} Masquerade={state.isMasquerade}', ephemeral=True)

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
	foundPlayer=False
	playerIndex=None
	global players
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundPlayer=True
			playerIndex=i
	if ((not gmRole in interaction.user.roles) and (not interaction.user.id==target.id)):
		await interaction.response.send_message('Only GMs can use this command on other people!', ephemeral=True)
	elif not foundPlayer:
		await interaction.response.send_message('This person is not in the list of active players!', ephemeral=True)
	else:
		tempPlayer=players[playerIndex]
		await interaction.response.send_message(f'{pprint.pformat(vars(tempPlayer), indent=2, sort_dicts=False)}', ephemeral=True)
		
@tree.command(
	name='toggle_dead',
	description='Sneakily mark a player as dead without the dead role. Only really useful during masquerade',
	guild=discord.Object(id=serverID)
			)
async def toggleDead(interaction, target :discord.Member):
	foundTarget=False
	targetIndex=None
	global players
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not gmRole in interaction.user.roles:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'The chosen member is not in the list of active players!', ephemeral=True)
	else:
		if players[targetIndex].isDead:
			players[targetIndex].isDead=False
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} is no longer dead!', ephemeral=True)
		else:
			players[targetIndex].isDead=True
			pSave(players, playersSaveFile)
			await interaction.response.send_message(f'{players[targetIndex].displayName} is now dead!', ephemeral=True)

@tree.command(
	name='call_meeting',
	description='Call emergency meeting if you\'re crewmate',
	guild=discord.Object(id=serverID)
			)
async def callMeeting(interaction, message :str=None):
	global players
	global state
	foundPlayer=False
	isAble=False
	for i, player in enumerate(players):
		if player.memID==interaction.user.id:
			meetingCallerIndex=i
			foundPlayer=True
			isAble = player.canCallMeeting

	if ((deadRole in interaction.user.roles) or (players[meetingCallerIndex].isDead)):
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
			description=f'{message}{os.linesep}It is now {state.returnDayState()}!',
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

	if not gmRole in interaction.user.roles:
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
	name="set_mask",
	description="GM command to set a user's mask",
	guild=discord.Object(id=serverID)
			)
async def setMask(interaction, target :discord.Member, mask_name :str, pfp :discord.Attachment):
	global players
	foundTarget=False
	targetIndex=None
	for i, p in enumerate(players):
		if target.id==p.memID:
			foundTarget=True
			targetIndex=i
		
	if not gmRole in interaction.user.roles:
		await interaction.response.send_message("Only GMs can use this command!", ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message("Your target was not in the list of active players!", ephemeral=True)
	else:
		players[targetIndex].maskName=mask_name
		players[targetIndex].maskImageURL=pfp.url
		pSave(players, playersSaveFile)
		await interaction.response.send_message("Set!", ephemeral=True)

@tree.command(
	name='mshoot',
	description='Use during masquerade to shoot a target mask',
	guild=discord.Object(id=serverID)
				)
async def maskedVigShot(interaction, target :str):
	global players
	global state
	foundShooter=False
	foundTarget=False
	shooterIndex=None
	targetIndex=None
	shooterHasAmmo=False

	for i, player in enumerate(players):
		if(player.memID==interaction.user.id):
			shooterIndex=i
			foundShooter=True
			shooterHasAmmo=player.canVigShot
		if(str(player.maskName).upper()==target.upper()):
			foundTarget=True
			targetIndex=i
	
	if not foundShooter:
		await interaction.response.send_message(f'You are not in the list of active players!', ephemeral=True)
	elif ((players[shooterIndex].maskName==None) or (players[shooterIndex].maskImageURL==None)):
		await interaction.response.send_message(f'You don\'t have a mask! Have a GM use /set_mask to give you one!', ephemeral=True)
	elif not foundTarget:
		await interaction.response.send_message(f'Could not find a mask with that name!', ephemeral=True)
	elif not shooterHasAmmo:
		await interaction.response.send_message(f'You don\'t have ammo for that!', ephemeral=True)
	elif ((deadRole in interaction.user.roles) or (players[shooterIndex].isDead)):
		await interaction.response.send_message(f'You can\'t shoot while dead!', ephemeral=True)
	elif players[targetIndex].isDead:
		await interaction.response.send_message(f'You can\'t shoot dead people!', ephemeral=True)
	elif state.phaseNumber<=1:
		await interaction.response.send_message(f'You can\'t shoot until Day 2!', ephemeral=True)
	elif not state.isDay:
		await interaction.response.send_message(f'You can only shoot during the day!', ephemeral=True)
	elif not state.isMasquerade:
		await interaction.response.send_message(f'You can only use this during masquerades! Instead, right click your victim and use apps->Shoot this player.', ephemeral=True)
	else:
		await dayChannel.set_permissions(interaction.guild.default_role, send_messages=False)
		state.advancePhase()
		embed=discord.Embed(
			title=f'***BANG***',
			description=f'{players[shooterIndex].maskName} has shot {players[targetIndex].maskName} to death!{os.linesep}It is {state.returnDayState()}!{os.linesep}',
			color=discord.Colour.blue()
							)
		embed.set_author(
			name="Michael",
			icon_url="https://smtd.umich.edu/wp-content/uploads/2022/06/mcelroy-crop.png"
						)
		await dayChannel.send(f'', embed=embed)

		players[shooterIndex].canVigShot=False
		players[targetIndex].isDead=True
		pSave(players, playersSaveFile)
		pSave(state, stateSaveFile)
		await interaction.response.send_message(f'You successfully shot your target!', ephemeral=True)

@tree.command(
	name='m',
	description='Use your mask to talk in day chat. Only works during Masquerades.',
	guild=discord.Object(id=serverID)
			)
async def maskChat(interaction, message :str, attachment :discord.Attachment=None):
	global players
	foundSpeaker=False
	speakerIndex=None
	await interaction.response.defer(ephemeral=True)
	
	for i, p in enumerate(players):
		if interaction.user.id==p.memID:
			foundSpeaker=True
			speakerIndex=i
	if not foundSpeaker:
		await interaction.followup.send(f'You are not in the list of active players!', ephemeral=True)
	elif (players[speakerIndex].maskName==None or players[speakerIndex].maskImageURL==None):
		await interaction.followup.send(f'You don\'t have a mask set up! Have a GM use /set_mask to give you one!', ephemeral=True)
	elif not state.isMasquerade:
		await interaction.followup.send(f'This command can only be used during masquerades!', ephemeral=True)
	elif not state.isDay:
		await interaction.followup.send(f'You can only do this during the day!', ephemeral=True)
	else:
		async with aiohttp.ClientSession() as session:
			if ((deadRole in interaction.user.roles) or (players[speakerIndex].isDead)):
				webhook=Webhook.from_url(raveyardWebhookURL, session=session)
				await webhook.send(message, username=players[speakerIndex].maskName, avatar_url=players[speakerIndex].maskImageURL)
				if not attachment==None:
					await webhook.send(attachment.url, username=players[speakerIndex].maskName, avatar_url=players[speakerIndex].maskImageURL)
				await interaction.followup.send(f'***In Raveyard:*** {message}', ephemeral=True)
			else:
				webhook=Webhook.from_url(masqueradeWebhookURL, session=session)
				await webhook.send(message, username=players[speakerIndex].maskName, avatar_url=players[speakerIndex].maskImageURL)
				if not attachment==None:
					await webhook.send(attachment.url, username=players[speakerIndex].maskName, avatar_url=players[speakerIndex].maskImageURL)
				await interaction.followup.send(f'{message}', ephemeral=True)

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
	await interaction.response.defer(ephemeral=True)
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
	if not (state.isDay or state.freeComments):
		await interaction.followup.send(f'You can only send comments during the day or during I Talk Good!', ephemeral=True)
	elif not foundSender:
		await interaction.followup.send(f'You are not in the list of active players!', ephemeral=True)
	elif not foundRecipient:
		await interaction.followup.send(f'Your target is not in the list of active players!', ephemeral=True)
	elif not (senderHasComments or state.freeComments):
		await interaction.followup.send(f'You are out of comments!', ephemeral=True)
	elif ((deadRole in interaction.user.roles) or (players[senderIndex].isDead)):
		await interaction.followup.send(f'You can\'t send comments if you\'re dead!', ephemeral=True)
	elif ((deadRole in recipient.roles) or (players[recipientIndex].isDead)):
		await interaction.followup.send(f'Your recipient is dead!', ephemeral=True)
	elif recipientPlayerChannel==None:
		await interaction.followup.send(f'Your recipient doesn\'t have a player channel! Have a gm use /set_player_channel to give them one!', ephemeral=True)
	elif senderPlayerChannel==None:
		await interaction.followup.send(f'You don\'t have a player channel! Have a GM use /set_player_channel to give you one!', ephemeral=True)
	elif state.isMasquerade:
		await interaction.followup.send(f'It\'s a masquerade! Use /mcomment to send a comment between masks!', ephemeral=True)
	else:

		if anon:
			sentAs='Anon'
		else:
			sentAs=interaction.user.display_name
			
		outboundEmbed=discord.Embed(
			title=f'',
			description=f'{message}',
			color=discord.Colour.blue()
									)
		loggedEmbed=discord.Embed(
			title=f'**You commented {players[recipientIndex].displayName}** as {sentAs}',
			description=f'{message}',
			color=discord.Colour.green()
									)
		overheardEmbed=discord.Embed(
			title=f'**You overhead a comment:**',
			description=f'{message}',
			color=discord.Colour.red()
									)

		messageText=''
		if not attachment==None:
			if 'image' in attachment.content_type:
				outboundEmbed.set_image(url=attachment.url)
				loggedEmbed.set_image(url=attachment.url)
				overheardEmbed.set_image(url=attachment.url)

		if anon:
			outboundEmbed.set_author(name=f'Anon', icon_url='https://creazilla-store.fra1.digitaloceanspaces.com/emojis/44265/disguised-face-emoji-clipart-md.png')
		else:
			outboundEmbed.set_author(name=f'{interaction.user.display_name}', icon_url=interaction.user.avatar.url)

		await recipientPlayerChannel.send(f'', embed=outboundEmbed)
		await senderPlayerChannel.send(f'', embed=loggedEmbed)

		if wasOverheard:
			await overheardIn.send(f'', embed=overheardEmbed)
		if not state.freeComments:
			players[senderIndex].commentsRemaining-=1
			await interaction.followup.send(f'Sent! You have {players[senderIndex].commentsRemaining} comments remaining!', ephemeral=True)
		else:
			await interaction.followup.send(f'Sent!', ephemeral=True)
		pSave(players, playersSaveFile)

@tree.command(
	name='mcomment',
	description='Comments, but with a *mask!*',
	guild=discord.Object(id=serverID)
			)
async def maskedComment(interaction, recipient :str, anon :bool=True, message :str=None, attachment :discord.Attachment=None):
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
	recipientMemberObject=None
	wasOverheard=False
	overheardIn=None
	await interaction.response.defer(ephemeral=True)
	for i, player in enumerate(players):
		if player.memID==interaction.user.id:
			foundSender=True
			senderIndex=i
			if player.commentsRemaining>0:
				senderHasComments=True
			if str(player.memID) in playerChannels:
				senderPlayerChannel=client.get_channel(playerChannels[str(player.memID)])
		if str(player.maskName).upper()==recipient.upper():
			foundRecipient=True
			recipientIndex=i
			print(f'player object display name: {player.displayName} player.memID: {player.memID}')
			if str(player.memID) in playerChannels:
				recipientPlayerChannel=client.get_channel(playerChannels[str(player.memID)])
				recipientMemberObject=thisServer.get_member(player.memID)
				print(f'recipient player channel name: {recipientPlayerChannel.name}')

	for i, player in enumerate(players):
		if(player.canOverhear and (not i==senderIndex) and (not i==recipientIndex)):
			if str(player.memID) in playerChannels:
				wasOverheard=True
				overheardIn=client.get_channel(playerChannels[str(player.memID)])
	if not (state.isDay or state.freeComments):
		await interaction.followup.send(f'You can only send comments during the day or night 1!', ephemeral=True)
	elif not foundSender:
		await interaction.followup.send(f'You are not in the list of active players!', ephemeral=True)
	elif not foundRecipient:
		await interaction.followup.send(f'Could not locate anyone wearing that mask!', ephemeral=True)
	elif not (senderHasComments or state.freeComments):
		await interaction.followup.send(f'You are out of comments!', ephemeral=True)
	elif ((deadRole in interaction.user.roles) or (players[senderIndex].isDead)):
		await interaction.followup.send(f'You can\'t send comments if you\'re dead!', ephemeral=True)
	elif ((deadRole in recipientMemberObject.roles) or (players[recipientIndex].isDead)):
		await interaction.followup.send(f'Your recipient is dead!', ephemeral=True)
	elif recipientPlayerChannel==None:
		await interaction.followup.send(f'Your recipient doesn\'t have a player channel! Have a gm use /set_player_channel to give them one!', ephemeral=True)
	elif senderPlayerChannel==None:
		await interaction.followup.send(f'You don\'t have a player channel! Have a GM use /set_player_channel to give you one!', ephemeral=True)
	elif not state.isMasquerade:
		await interaction.followup.send(f'We are not at a masquerade. :pensive: You\'ll have to use boring old regular /comment', ephemeral=True)
	else:

		if anon:
			sentAs='Anon'
		else:
			sentAs=players[senderIndex].maskName

		outboundEmbed=discord.Embed(
			title=f'',
			description=f'{message}',
			color=discord.Colour.blue()
									)
		loggedEmbed=discord.Embed(
			title=f'**You commented {players[recipientIndex].maskName}** as {sentAs}',
			description=f'{message}',
			color=discord.Colour.green()
									)
		overheardEmbed=discord.Embed(
			title=f'**You overhead a comment:**',
			description=f'{message}',
			color=discord.Colour.red()
									)

		messageText=''
		if not attachment==None:
			if 'image' in attachment.content_type:
				outboundEmbed.set_image(url=attachment.url)
				loggedEmbed.set_image(url=attachment.url)
				overheardEmbed.set_image(url=attachment.url)

		if anon:
			outboundEmbed.set_author(name=f'Anon', icon_url='https://creazilla-store.fra1.digitaloceanspaces.com/emojis/44265/disguised-face-emoji-clipart-md.png')
		else:
			outboundEmbed.set_author(name=f'{sentAs}', icon_url=players[senderIndex].maskImageURL)

		await recipientPlayerChannel.send(f'', embed=outboundEmbed)
		await senderPlayerChannel.send(f'', embed=loggedEmbed)
		if wasOverheard:
			await overheardIn.send(f'', embed=overheardEmbed)
		if not state.freeComments:
			players[senderIndex].commentsRemaining-=1
			await interaction.followup.send(f'Sent! You have {players[senderIndex].commentsRemaining} comments remaining!', ephemeral=True)
		else:
			await interaction.followup.send(f'Sent!', ephemeral=True)
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
	if not gmRole in interaction.user.roles:
		await interaction.response.send_message(f'Only GMs can use this command!', ephemeral=True)
	else:
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
	shooterHasAmmo=False

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
	elif ((deadRole in interaction.user.roles) or (players[shooterIndex].isDead)):
		await interaction.response.send_message(f'You can\'t shoot while dead!', ephemeral=True)
	elif ((deadRole in target.roles) or (players[targetIndex].isDead)):
		await interaction.response.send_message(f'You can\'t shoot dead people!', ephemeral=True)
	elif state.phaseNumber<=1:
		await interaction.response.send_message(f'You can\'t shoot until Day 2!', ephemeral=True)
	elif not state.isDay:
		await interaction.response.send_message(f'You can only shoot during the day!', ephemeral=True)
	elif state.isMasquerade:
		await interaction.response.send_message(f'You can\'t use this during masquerades! Use /mshoot instead.', ephemeral=True)
	else:
		await dayChannel.set_permissions(interaction.guild.default_role, send_messages=False)
		state.advancePhase()
		embed=discord.Embed(
			title=f'***BANG***',
			description=f'{interaction.user.display_name} has shot {target.display_name} to death!{os.linesep}It is {state.returnDayState()}!{os.linesep}',
			color=discord.Colour.blue()
							)
		embed.set_author(
			name="Michael",
			icon_url="https://smtd.umich.edu/wp-content/uploads/2022/06/mcelroy-crop.png"
						)
		await dayChannel.send(f'', embed=embed)

		players[shooterIndex].canVigShot=False
		await target.add_roles(deadRole)
		players[targetIndex].isDead=True
		pSave(players, playersSaveFile)
		pSave(state, stateSaveFile)
		await interaction.response.send_message(f'You successfully shot your target!', ephemeral=True)

#v----- TOGGLERS -----v
@tree.context_menu(
	name="Toggle Meetings",
	guild=discord.Object(id=serverID)
				)
async def toggleCanMeeting(interaction, target :discord.Member):
	foundTarget=False
	targetIndex=None
	global players
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not gmRole in interaction.user.roles:
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
	foundTarget=False
	targetIndex=None
	global players
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not gmRole in interaction.user.roles:
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
	foundTarget=False
	targetIndex=None
	global players
	for i, p in enumerate(players):
		if p.memID==target.id:
			foundTarget=True
			targetIndex=i
	if not gmRole in interaction.user.roles:
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

##################################################
#####             CHAT COMMANDS              #####
##################################################
@client.event
async def on_message(message):
	global players
	global state

	if(message.author==client.user):
		return

	if(message.content=='/initPlayers'):
		if gmRole in message.author.roles:
			players=[]
			for member in message.guild.members:
				if playingRole in member.roles:
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

	if(message.content=='/viewDayChannel'):
		if gmRole in message.author.roles:
			await logChannel.send(f'{message.author.mention}{dayChannel.name}')
		await message.delete()

	if(message.content=='/advancePhase'):
		if not gmRole in message.author.roles:
			await message.delete()
		else:
			oldPhaseNumber=state.phaseNumber
			state.advancePhase()
			newPhaseNumber=state.phaseNumber
			if not (newPhaseNumber==oldPhaseNumber):
				for p in players:
					p.commentsRemaining=3
				if newPhaseNumber==1:
					state.freeComments=True
				else:
					state.freeComments=False
			else:
				try:
					await dayChannel.set_permissions(interaction.guild.default_role, send_messages=False)
				except:
					await logChannel.send(f'Couldn\'t lock day channel. Does it exist? Check with !viewDayChannel')
			pSave(players, playersSaveFile)
		pSave(state, stateSaveFile)
		await logChannel.send(f'{message.author.display_name} advanced the phase! It is now {state.returnDayState()}!')
		await message.delete()

	if(message.content=='/resetState'):
		if not gmRole in message.author.roles:
			await message.delete()
		else:
			state.resetState()
			await logChannel.send(f'{message.author.mention} has reset to Night 0 with no day channel, free comments, and no masquerade!')
			pSave(state, stateSaveFile)
			await message.delete()

	if(message.content=="/toggleDay"):
		if not gmRole in message.author.roles:
			await message.delete()
		else:
			if state.isDay:
				state.isDay=False
			else:
				state.isDay=True
			pSave(state, stateSaveFile)
			await logChannel.send(f'{message.author.mention} toggled day/night, making it {state.returnDayState()}!')
			await message.delete()

	if(message.content=='/toggleFreeComments'):
		if not gmRole in message.author.roles:
			await message.delete()
		else:
			if state.freeComments:
				state.freeComments=False
			else:
				state.freeComments=True
			pSave(state, stateSaveFile)
			await logChannel.send(f'{message.author.mention} has set free comments to {state.freeComments}!')
			await message.delete()

	if(message.content=='/toggleMasquerade'):
		if not gmRole in message.author.roles:
			await message.delete()
		else:
			if state.isMasquerade:
				state.isMasquerade=False
			else:
				state.isMasquerade=True
			pSave(state, stateSaveFile)
			await logChannel.send(f'{message.author.mention} has set masquerade mode to {state.isMasquerade}!')
			await message.delete()


#v-----Run when bot is ready -----v
@client.event
async def on_ready():
	global logChannel
	global dayChannel
	global gmRole
	global deadRole
	global playingRole
	global serverID
	global thisServer
	logChannel=client.get_channel(logChannelID)
	dayChannel=client.get_channel(state.dayChannelID)
	for guild in client.guilds:
		if guild.id==serverID:
			thisServer=guild
	gmRole=discord.utils.get(thisServer.roles,name="Game Master")
	deadRole=discord.utils.get(thisServer.roles,name="Dead")
	print(deadRole.name)
	playingRole=discord.utils.get(thisServer.roles,name="Playing")
	await tree.sync(guild=discord.Object(id=serverID))
	print('Bot is ready!')

client.run(botToken)