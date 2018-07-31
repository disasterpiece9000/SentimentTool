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
	global current_users
	expired_users = []
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
	return expired_users

#main method for account analysis
def analyzeUsers(users):
	print ('Analyzing all users in current list: ' + str(len(users)))
	for user in users:
		#used to implement small version of karma breakdown if necessairy
		flair_count = 0
		#scrape user's comments and posts
		hist_info = analyzeUserHist(user)
		#hist_info returns karma breakdown by crypto, T/F value for flair assignment, and a count of total posts and submissions
		karma_stats = hist_info.pop(0)
		sent_flair = hist_info.pop(0)
		total_submis = hist_info.pop(0)
		if sent_flair == True:
			flair_count += 1
		#flairs user for account < 1 yr.
		age_flair = analyzeUserAge(user)
		if age_flair == True:
			flair_count += 1
		#flairs user for karma < 1k
		if user.comment_karma < 1000:
			appendFlair(user, str(user.comment_karma) + ' cmnt karma')
			flair_count += 1
		#if user has attribute 'New to crypto' then don't add karma breakdown
		if total_submis > 15:
			small = False
			#if there are 2+ flair attributes already then use condensed version
			if flair_count >= 2:
				small = True
			analyzeUserKarma(user, karma_stats, small)
		else:
			appendFlair(user, 'New to crypto')
		updateDB(user, total_submis)

#sentiment analysis of expired_users
def analyzeUserHist(user):
	global users_and_flair, relevantSubs

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
	flaired = sentFlair(user, count, countPos, countNeg, totalNeg, totalPos)
	
	totalPost = postCount + count
	return [sub_counter, flaired, totalPost]
	
#flair new accounts
def analyzeUserAge(user):
	username = str(user)
	userCreated = datetime.fromtimestamp(user.created)
	tdelta = relativedelta.relativedelta(current_time, userCreated)
	flaired = False
	#create flair with appropriate time breakdown
	if tdelta.years < 1:
		flaired = True
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
	return flaired

def analyzeUserKarma(user, sub_counter, small):
	parent_sub = 'CM'
	hold_flair = parent_sub + ': ' + str(sub_counter[parent_sub]) + ' karma'
	
	if small == True:
		neg_flair = False
		neg_score = 0
		neg_sub = ''
		for key, value in sub_counter.most_common():
			if value < -10 and value < neg_score and key != parent_sub:
				neg_score = value
				neg_sub = key
				neg_flair = True
		if neg_flair == True:
			hold_flair += ' ' + neg_sub + ': ' + str(neg_score) + ' karma'
			appendFlair(user, hold_flair)
		else:
			for key, value in sub_counter.most_common(1):
				if value > 500 and key != parent_sub:
					hold_flair += ' ' + key + ': ' + str(value) + ' karma'
			appendFlair(user, hold_flair)
		
	else:
		#Add flair for sub karma > 1k	
		for key, value in sub_counter.most_common(2):
			if value > 500 and key != parent_sub:
				hold_flair += ' ' + key + ': ' + str(value) + ' karma'
		#Add flair for sub karma < -10
		for key, value in sub_counter.most_common():
			if value < -10 and key != parent_sub:
				hold_flair += ' ' + key + ': ' + str(value) + ' karma'
		appendFlair(user, hold_flair)

#Calculate Positive/Negative score from passed values
def sentFlair(user, count, countPos, countNeg, totalNeg, totalPos):
	username = str(user)
	flaired = False
	#Require at least 15 comments for accurate analysis
	if count > 15:
		sentPerc = ((countPos + countNeg) / float(count)) * 100
		#Require at least 7.5% of comments to show obvious sentiment
		if sentPerc < 7.5:
			print ('\t' + username + ': Not enough sentiment ' + str(sentPerc)[:4] + '% Count: ' + str(count))
			return flaired
		posPerc = (countPos/float(countPos + countNeg)) * 100
		negPerc = (countNeg/float(countPos + countNeg)) * 100
		diffPerc = posPerc - negPerc

		if diffPerc < 0:
			#If there are 20% more negative comments than positive then flair user as negative
			if diffPerc < -20:
				appendFlair(user, 'Negative')
				print ('\t' + username + ': Negative ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4])
				flaired = True
			#else:
				#print ('\t' + username + ': avgNeg: ' + str(avgNeg) + ' diffPerc: ' + str(diffPerc))

		elif diffPerc > 0:
			#If there are 35% more positive comments than negative then flair user as positive
			if diffPerc > 35:
				appendFlair(user, 'Positive')
				flaired = True
				print ('\t' + username + ': Positive ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4])
			#else:
				#print ('\t' + username + ': avgPos: ' + str(avgPos) + ' diffPerc: ' + str(diffPerc))
		else:
			print ('\t' + username + ': Unknown ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4] + ' CountSent: ' + str(countPos + countNeg))
	return flaired

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
def updateDB(user, total_submis):
	username = str(user)
	flair_time = json_serial(current_time)
	userDB.insert({'username' : username, 'flair_age' : flair_time, 'submis_count': total_submis})

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

#turn list of usernames into user object and don't check if they exist	
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
#list of mods to accept PMs from
mods = setAccnts({'_CapR_', 'turtleflax', 'PrinceKael', 'Christi123321', ' publicmodlogs', 'AutoModerator', 'CryptoMarketsMod', 'davidvanbeveren', 'trailblazerwriting', 'golden_china', 'PhantomMod'})
#get command line arg
command = sys.argv[1]
#continuously scrape subreddit and apply flair to new users
if command == 'auto':
	while True:
		readPMs()
		readFiles()
		expired = findExpiredUsers(300, 100)
		analyzeUsers(expired)
		flairUsers()
#one sweep of max posts and comments
elif command == 'big':
	readPMs()
	readFiles()
	expired = findExpiredUsers(None, None)
	analyzeUsers(expired)
	flairUsers()
#small sweep for testing or low activity subs
elif command == 'small':
	readPMs()
	readFiles()
	expired = findExpiredUsers(5, 5)
	analyzeUsers(expired)
	flairUsers()
#manually apply flair to a user
elif command == 'manual':
	targetName = sys.argv[2]
	target = setUser(targetName)
	if target != None:
		target_list = [target]
		analyzeUsers(target_list)
		flairUsers()
#manually add a user to the whitelist
elif command == 'whitelist':
	targetName = sys.argv[2]
	addWhitelist(targetName)
#print guide to command line arguments
else:
	print ('No arg given. Better luck next time\nArgs:\n\tflair - scrape target sub for expired users\n\tmanual  someuser- manually flair a user\n\twhitelist someuser - add a user to the whitelist')
