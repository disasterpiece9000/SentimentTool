# coding: utf-8

#imports
import praw
import prawcore
import sys
import time
import json
from collections import Counter
from datetime import datetime, date
from dateutil import relativedelta
import dateutil.parser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize
from tinydb import TinyDB, Query

#sentiment analyzer
sid = SentimentIntensityAnalyzer()

#lists of users for filters
current_users = []
expired_users = []
users_and_flair = {}
whitelist = []

#Subreddit's with corresponding abreviations
sub_abrev = {
	'CRYPTOCURRENCY': 'CC','CRYPTOMARKETS': 'CM','CRYPTOTECHNOLOGY': 'CT','BLOCKCHAIN': 'Blockchain',
	'ALTCOIN': 'ALT','BITCOIN' : 'BTC','BITCOINMARKETS': 'BTC','LITECOIN': 'LTC','LITECOINMARKETS': 'LTC',
	'BITCOINCASH': 'BCH','BTC': 'BTC','ETHEREUM': 'ETH','ETHTRADER': 'ETH','RIPPLE': 'Ripple','STELLAR': 'XLM',
	'VECHAIN': 'VEN','VERTCOIN': 'VTC', 'VERTCOINTRADER': 'VTC','DASHPAY': 'Dashpay', 'MONERO': 'XMR', 
	'XRMTRADER': 'XRM', 'NANOCURRENCY': 'NANO','WALTONCHAIN': 'WTC', 'IOTA': 'MIOTA', 'IOTAMARKETS': 'MIOTA', 
	'LISK': 'LSK', 'DOGECOIN': 'DOGE', 'DOGEMARKET': 'DOGE', 'NEO': 'NEO', 'NEOTRADER':'NEO', 'CARDANO': 'ADA',
	'VERGECURRENCY': 'XVG', 'ELECTRONEUM': 'ETN', 'DIGIBYTE': 'DGB', 'ETHEREUMCLASSIC': 'ETC', 'OMISE_GO': 'OMG',
	'NEM': 'XEM', 'MYRIADCOIN': 'XMY', 'NAVCOIN': 'NAV', 'NXT': 'NXT', 'POETPROJECT': 'poetproject', 'ZEC': 'ZEC', 
	'GOLEMPROJECT': 'GNT', 'FACTOM': 'FCT', 'QTUM': 'QTUM', 'AUGUR': 'AU', 'CHAINLINK': 'LINK', 
	'LINKTRADER': 'LINK', 'XRP': 'XRP', 'TRONIX': 'Tronix', 'EOS': 'EOS', '0XPROJECT': 'ZRX', 'ZRXTRADER': 'ZRX',
	'KYBERNETWORK': 'KNC', 'ZILLIQA': 'ZIL', 'STRATISPLATFORM': 'STRAT', 'WAVESPLATFORM': 'WAVES',
	'WAVESTRADER': 'WAVES', 'ARDOR': 'ARDR', 'SYSCOIN': 'SYS', 'PARTICL': 'PART', 'BATPROJECT': 'BATProject',
	'ICON': 'ICX', 'HELLOICON': 'ICX', 'GARLICOIN': 'GRLC', 'BANCOR': 'BNT', 'PIVX': 'PIVX', 'WANCHAIN': 'WAN',
	'KOMODOPLATFORM': 'KMD', 'ENIGMAPROJECT': 'ENG', 'ETHOS_IO': 'ETHOS', 'DECENTRALAND': 'MANA',
	'NEBULAS': 'NAS', 'ARKECOSYSTEM': 'ARK', 'FUNFAIRTECH': 'FUN', 'STATUSIM': 'SNT', 'DECRED': 'DCR',
	'DECENTPLATFORM': 'DCT', 'ONTOLOGY': 'ONT', 'AETERNITY': 'AE', 'SIACOIN': 'SC', 'SIATRADER': 'SC',
	'STORJ': 'STORJ', 'SAFENETWORK': 'SafeNetwork', 'PEERCOIN': 'PPC', 'NAMECOIN': 'NMC', 'STEEM': 'STEEM',
	'REQUESTNETWORK': 'REQ', 'OYSTER': 'PRL', 'KINFOUNDATION': 'KIN', 'ICONOMI': 'ICN', 'GENESISVISION': 'GVT',
	'BEST_OF_CRYPTO': 'BestOf', 'BITCOINMINING': 'BitcoinMining', 'CRYPTORECRUITING': 'CryptoRecruting',  
	'DOITFORTHECOIN': 'DoItForTheCoin', 'JOBS4CRYPTO': 'Jobs4Crypto', 'JOBS4BITCOIN': 'Jobs4Bitcoin', 
	'LITECOINMINING': 'LTC', 'OPENBAZAAR': 'OpenBazzar', 'GPUMINING': 'GPUMining', 'BINANCEEXCHANGE': 'BNB', 
	'BINANCE': 'BNB', 'ICOCRYPTO': 'icocrypto','LEDGERWALLET': 'LedgerWallet', 'CRYPTOTRADE': 'CryptoTrade',
	'BITCOINBEGINNERS': 'BitcoinBeginners', 'ETHERMINING': 'ETH','MONEROMINING': 'XRM', 'ETHEREUMNOOBIES': 'ETH', 
	'KUCOIN': 'Kucoin', 'COINBASE': 'Coinbase', 'ETHERDELTA': 'EtherDelta'
		}	
	
#save current time
current_time = datetime.now()

#start instance of Reddit
reddit = praw.Reddit('SentimentBot')

#subreddit for scraping/flairs
cc_sub = reddit.subreddit('cryptomarkets')

#initialize TInyDB and load databases
userDB = TinyDB('userDB.json')
whitelistDB = TinyDB('whitelist.json')
find_stuff = Query()

#read users from databases
def readFiles():
	global current_users, users_and_flair, current_time, whitelist
	#update globals
	current_time = datetime.now()
	current_users.clear()
	expired_users.clear()
	users_and_flair.clear()
	whitelist.clear()
	
	for user in userDB:
		tdelta = current_time - dateutil.parser.parse(user['flair_age'])
		#remove users with expired flair and add current users to list
		if tdelta.days > 7:
			print (user['username'] + ' has old flair')
			userDB.remove(find_stuff['username'] == user['username'])
		else:
			userObj = setUser(user['username'])
			#check if user is valid
			if userObj != None:
				current_users.append(userObj)
	print ('Read all current users')
	
	for username in whitelistDB:
		user = setUser(username['username'])
		if user != None and user not in whitelist:
			whitelist.append(user)
	print ('All users read from whitelist')

#scrape main sub for users not in current_users and not already in expired_users
def findExpiredUsers(cmnt_limit, post_limit):
	global current_users, expired_users
	print ('Scraping comments')
	for comment in cc_sub.comments(limit = cmnt_limit):
		user = comment.author
		username = str(user)
		if user not in current_users and user not in expired_users and user not in whitelist and checkUser(user) == True:
			expired_users.append(user)
			print ('\tNew user added to expired list: ' + username)

	print ('Scraping submissions')
	for post in cc_sub.new(limit = post_limit):
		user = post.author
		username = str(user)
		if user not in current_users and user not in expired_users and user not in whitelist and checkUser(user) == True:
			expired_users.append(user)
			print ('\tNew user added to expired list: ' + username)

#sentiment analysis of expired_users
def analyzeUserHist(users):
	global users_and_flair, relevantSubs
	print ('Analyzing all users in current list: ' + str(len(users)))
	userCount = 0

	for user in users:
		updateDB(user)
		username = str(user)
		#Setup float and int numbers for sentiment analysis
		sub_counter = Counter()
		userSent = 0.0
		count = 0
		countNeg = 0
		countPos = 0
		totalNeg = 0.0
		totalPos = 0.0
		postCount = 0
		
		#Analyze a users comments
		comments = user.comments.new(limit = None)
		for comment in comments:
			cmnt_sub = comment.subreddit
			sub_name = str(cmnt_sub).upper()
			if sub_name in sub_abrev:
				commentSent = analyzeText(comment.body)
				count += 1
				if commentSent < -0.5:
					countNeg += 1
					totalNeg += commentSent
				elif commentSent > 0.6:
					countPos += 1
					totalPos += commentSent
				#Count comment's karma in sub
				abrev = sub_abrev[sub_name]
				sub_counter[abrev] += comment.score
		
		#Count post's karma in sub
		posts = user.submissions.new(limit = None)
		for post in posts:
			post_sub = post.subreddit
			sub_name = str(post_sub).upper()
			if sub_name in sub_abrev:
				postCount += 1
				abrev = sub_abrev[sub_name]
				sub_counter[abrev] += post.score
		
		#analyze sentiment statistics
		sentFalir(user, count, postCount, countPos, countNeg, totalNeg, totalPos)
		
		#Add flair for sub karma > 1k	
		for key, value in sub_counter.most_common(2):
			if value > 500:
				flairText = key + ': ' + str(value) + ' karma'
				appendFlair(user, flairText)
		#Add flair for sub karma < -10
		for key, value in sub_counter.most_common():
			if value < -10:
				flairText = key + ': ' + str(value) + ' karma'
				appendFlair(user, flairText)

#get data from sources other than comments and posts
def analyzeUserStats(users):
	for user in users:
		username = str(user)

		#flair new accounts
		userCreated = datetime.fromtimestamp(user.created)
		now = datetime.now()
		tdelta = relativedelta.relativedelta(now, userCreated)
		#create flair with appropriate time breakdown
		if tdelta.years < 1:
			if tdelta.months < 1:
				days = tdelta.days
				flairText = 'Redditor for ' + str(days)
				if days == 1:
					appendFlair(username, flairText + ' day')
				else:
					appendFlair(username, flairText + ' days')
			else:
				months = tdelta.months
				flairText = 'Redditor for ' + str(months)
				if months == 1:
					appendFlair(user, flairText + ' month')
				else:
					appendFlair(user, flairText + ' months')
		#flair low comment karma
		if user.comment_karma < 1000:
			appendFlair(user, str(user.comment_karma) + ' cmnt karma')

#Calculate Positive/Negative score from passed values
def sentFalir(user, count, postCount, countPos, countNeg, totalNeg, totalPos):
	username = str(user)
	#Require at least 15 comments for accurate analysis
	if count > 15:
		sentPerc = ((countPos + countNeg) / float(count)) * 100
		#Require at least 7.5% of comments to show obvious sentiment
		if sentPerc < 7.5:
			print ('\t' + username + ': Not enough sentiment ' + str(sentPerc)[:4] + '% Count: ' + str(count))
			return
			
		posPerc = (countPos/float(countPos + countNeg)) * 100
		negPerc = (countNeg/float(countPos + countNeg)) * 100
		diffPerc = posPerc - negPerc

		if diffPerc < 0:
			#If there are 20% more negative comments than positive then flair user as negative
			if diffPerc < -20:
				appendFlair(user, 'Negative')
				print ('\t' + username + ': Negative ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4])
			#else:
				#print ('\t' + username + ': avgNeg: ' + str(avgNeg) + ' diffPerc: ' + str(diffPerc))

		elif diffPerc > 0:
			#If there are 35% more positive comments than negative then flair user as positive
			if diffPerc > 35:
				appendFlair(user, 'Positive')
				print ('\t' + username + ': Positive ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4])
			#else:
				#print ('\t' + username + ': avgPos: ' + str(avgPos) + ' diffPerc: ' + str(diffPerc))
		else:
			print ('\t' + username + ': Unknown ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4] + ' CountSent: ' + str(countPos + countNeg))
	#If user has less than 15 comments then flair user as new to crypto		
	elif postCount + count < 15:
		appendFlair(user, 'New to crypto')
		print ('\t' + username + ': Not enough comments Count: ' + str(count))

#Search PM's for new messages with the syntax '!whitelist /u/someuser and add someuser to the whitelist
def readPMs():
	messages = reddit.inbox.unread()
	for message in messages:
		command = message.body.split()
		if len(command) == 2 and message.author in mods:
			first = command.pop(0)
			second = command.pop(0)
			print ('Command: ' + first + ' ' + second)
			if first == "!whitelist":
				if second.startswith("/u/"):
					targetUser = second[3:]
				elif second.startswith("u/"):
					targetUser = second[2:]
				else:
					targetUser = second
				addWhitelist(targetUser)
				message.mark_read()
				print ('Message about: ' + second + ' was accepted and marked read')
		else:
			print ('Message was not accpeted and left unread')
	
#concatonate flair
def appendFlair(user, newFlair):
	username = str(user)
	if username in users_and_flair:
		holdFlair = users_and_flair[username]
		holdFlair += ' | ' + newFlair
		users_and_flair.update( {username : holdFlair})
	else:
		users_and_flair[username] = newFlair

#assign flair to users
def flairUsers():
	global users_and_flair
	print ('\nUsers and corresponding flair:')
	for username in users_and_flair:
		user = setUser(username)
		flair = users_and_flair[username]
		cc_sub.flair.set(user, flair)
		print (username + ': ' + flair)

#add users to database with flair
def updateDB(user):
	username = str(user)
	flair_time = json_serial(current_time)
	userDB.insert({'username' : username, 'flair_age' : flair_time})

#Add a username to the whitelistDB
def addWhitelist(username):
	whitelistDB.insert({'username' : username})
	whitelist.append(username)
	print (username + ' added to whitelist')

#convert datetime so databse can read it
def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

#preform text analysis of individual comment
def analyzeText(text):
	sentences = sent_tokenize(text)
	polarity = 0.0
	count = 0
	for sentence in sentences:
		holdPol = sid.polarity_scores(sentence)['compound']
		polarity += holdPol
		count += 1
	if count == 0:
		return 0
	return polarity/count

#turn list of strings into list of subreddit objects
def makeSubList(subList):
	returnList = []
	for sub in subList:
		returnList.append(reddit.subreddit(sub))
	return returnList

#turn username into user object and check if user exists
def setUser(username):
	try:
		return reddit.redditor(username)
	except (prawcore.exceptions.NotFound, AttributeError):
		return None
		
def setAccnts(usernames):
	return_list = []
	for username in usernames:
		return_list.append(reddit.redditor(username))
	return return_list
		
#check if user object is accessible
def checkUser(user):
	try:
		user.fullname
	except prawcore.exceptions.NotFound:
		return False
	return True

#main method
mods = setAccnts({'_CapR_', 'turtleflax', 'PrinceKael', 'Christi123321', ' publicmodlogs', 'AutoModerator', 'CryptoMarketsMod', 'davidvanbeveren', 'trailblazerwriting', 'golden_china'})
command = sys.argv[1]
#continuously scrape subreddit and apply flair to new users
if command == 'auto':
	while True:
		readPMs()
		readFiles()
		findExpiredUsers(300, 100)
		analyzeUserHist(expired_users)
		analyzeUserStats(expired_users)
		flairUsers()
elif command == 'big':
	readPMs()
	readFiles()
	findExpiredUsers(None, None)
	analyzeUserHist(expired_users)
	analyzeUserStats(expired_users)
	flairUsers()
#manually apply flair to a user
elif command == 'manual':
	targetName = sys.argv[2]
	target = setUser(targetName)
	if target != None:
		target_list = [target]
		analyzeUserHist(target_list)
		analyzeUserStats(target_list)
		flairUsers()
#manually add a user to the whitelist
elif command == 'whitelist':
	targetName = sys.argv[2]
	addWhitelist(targetName)
#print guide to command line arguments
else:
	print ('No arg given. Better luck next time\nArgs:\n\tflair - scrape target sub for expired users\n\tmanual  someuser- manually flair a user\n\twhitelist someuser - add a user to the whitelist')
