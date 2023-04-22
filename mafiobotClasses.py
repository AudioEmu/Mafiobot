class gameState:

	def __init__(self):
		self.isDay=False
		self.phaseNumber=0
		self.dayChannelID=None

	def resetState(self):
		self.isDay=False
		self.phaseNumber=0
		self.dayChannelID=None

	def advancePhase(self):
		if self.isDay:
			self.isDay=False
		else:
			self.isDay=True
			self.phaseNumber+=1

	def returnDayState(self):
		dayOrNight="Neither" #Not actually possible, I don't think. Don't know that I need this line
		if self.isDay:
			dayOrNight="Day"
		else:
			dayOrNight="Night"
		return(f'{dayOrNight} Phase {self.phaseNumber}')

class player:
	def __init__(self, name :str, displayName :str, memID :int):
		self.name=name
		self.displayName=displayName
		self.memID=memID
		self.commentsRemaining=0
		self.canOverhear=False
		self.canVigShot=False
		self.canCallMeeting=False
		self.parlayAmmo=0