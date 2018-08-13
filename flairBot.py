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

#Subreddit's with corresponding abreviations
sub_abrev = TinyDB

#save current time
current_time = datetime.now()

#start instance of Reddit
reddit = praw.Reddit('SentimentBot')

#initialize sub specific global variables
users_and_flair = {}
sub_abrev = {}
abrevDB = TinyDB('abrevDB.json')
for sub in abrevDB:
	sub_abrev[sub['sub']] = sub['abrev']
print ('Sub abreviations accepted')
find_stuff = Query()

#lists of mods
CMmods = ('_CapR_', 'turtleflax', 'PrinceKael', 'Christi123321', ' publicmodlogs', 'AutoModerator', 'CryptoMarketsMod', 'davidvanbeveren', 'trailblazerwriting', 'golden_china', 'PhantomMod')
CTmods = ('davidvanbeveren', '_CapR_', 'bLbGoldeN', 'AtHeartEngineer', 'TheRetroguy', 'turtleflax', 'LacticLlama', 'ndha1995', 'Neophyte-', 'AutoModerator', 'CryptoTechnologyMod', 'publicmodlogs')
CCmods = ('SeasonFinale', 'stardigrada', 'PhantomMod', 'jwinterm', 'crypto_buddha', 'socialcadabra', 'SamsumgGalaxyPlayer', 'INGWR', 'doug3465', 'AdamSC1', '_I_Am_Chaos_', 'PrinceKael', 'wannabelikeme',
'CryptoMaximalist', 'LargeSnorlax', 'millerb7', 'macktastick', 'CryptoCurrencyMod', 'AutoModerator', 'ccticker', 'publicmodlogs', '_ihavemanynames_', 'Professional-Kiwi', 'CCNewsBot', 'shimmyjimmy97')

#subs and whitelist CSS
CCcss = ('Trophybronze', 'Trophysilver', 'Trophygold')
CMcss = ('Bitcoin')
CTcss = ()

#sub specific rule sets
CTrules = {'sentiment': True, 'karma_breakdown': True, 'comment_karma': True, 'accnt_age': True, 'new': True}
CMrules = {'sentiment': True, 'karma_breakdown': True, 'comment_karma': True, 'accnt_age': True, 'new': True}
CCrules = {'sentiment': True, 'karma_breakdown': True, 'comment_karma': True, 'accnt_age': True, 'new': True}

#sub lists
subs = ['CryptoCurrency', 'CryptoMarkets', 'CryptoTechnology']
subs_and_userDB = {'CryptoCurrency': 'CCuserDB', 'CryptoMarkets': 'CMuserDB', 'CryptoTechnology': 'CTuserDB'}
subs_and_whitelist = {'CryptoCurrency': 'CCwhitelist', 'CryptoMarkets': 'CMwhitelist', 'CryptoTechnology': 'CTwhitelist'}
subs_and_mods = {'CryptoCurrency': CCmods, 'CryptoMarkets': CMmods, 'CryptoTechnology': CTmods}
subs_and_css = {'CryptoCurrency': CCcss, 'CryptoMarkets': CMcss, 'CryptoTechnology': CTcss}
subs_and_rules = {'CryptoCurrency': CCrules, 'CryptoMarkets': CMrules, 'CryptoTechnology': CTrules}

#read users from databases
def readUserDB(sub_name):
	returnList = []
	userDB = TinyDB(subs_and_userDB[sub_name] + '.json')

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
				returnList.append(userObj)
	print ('Read all current users')
	return returnList

def readWhitelistDB(sub_name):
	returnList = []
	whitelistDB = TinyDB(subs_and_whitelist[sub_name] + '.json')

	for username in whitelistDB:
		user = setUser(username['username'])
		if user != None:
			returnList.append(user)
	print ('All users read from whitelist')
	return returnList


#scrape main sub for users not in current_users and not already in expired_users
def findExpiredUsers(parent_sub, cmnt_limit, post_limit, current_users, whitelist):
	expired_users = []
	sub = reddit.subreddit(parent_sub)
	css_whitelist = subs_and_css[parent_sub]
	css_and_text = {}
	templates = list(sub.flair.templates)
	for template in templates:
		css_and_text[template['flair_css_class']] = template['flair_text']

	print ('Scraping comments')
	for comment in sub.comments(limit = cmnt_limit):
		user = comment.author
		username = str(user)
		#user_css = (next(sub.flair(user))['flair_css_class'])

		#if user_css == None:
		#	user_css = 'my fears were valid'

		#if user_css in css_whitelist and user not in whitelist:
		#	addWhitelist(username, parent_sub, whitelist)
		#	sub.flair.set(user, css_and_text[user_css], user_css)
		#	print ('\tNew user added to whitelist and flair set to default')
		if user not in current_users and user not in expired_users and user not in whitelist and checkUser(user) == True:
			expired_users.append(user)
			print ('\tNew user added to expired list: ' + username)

	print ('Scraping submissions')
	for post in sub.new(limit = post_limit):
		user = post.author
		username = str(user)
		#user_css = (next(sub.flair(user))['flair_css_class'])

		#if user_css == None:
		#	user_css = 'my fears were valid'
		#
		#if user_css in css_whitelist and user not in whitelist:
		#	addWhitelist(username, parent_sub, whitelist)
		#	sub.flair.set(user, css_and_text[user_css], user_css)
		#	print ('\tNew user added to whitelist and flair set to default')
		if user not in current_users and user not in expired_users and user not in whitelist and checkUser(user) == True:
			expired_users.append(user)
			print ('\tNew user added to expired list: ' + username)
	return expired_users

def clearWhitelistFlair(parent_sub, whitelist):
	sub = reddit.subreddit(parent_sub)
	for user in whitelist:
		user_css = (next(sub.flair(user))['flair_css_class'])
		sub.flair.set(user, '', user_css)
	print ("Whitelist users' flair cleared")


#main method for account analysis
def analyzeUsers(users, users_and_flair, parent_sub):
	#Rules for what flair attributes are used
	sub_rules = subs_and_rules[parent_sub]
	print ('Analyzing all users in current list: ' + str(len(users)))
	for user in users:
		#used to implement small version of karma breakdown if necessairy
		flair_count = 0
		#hist_info returns karma breakdown by crypto, T/F value for flair assignment, and a count of total posts and submissions
		hist_info = analyzeUserHist(user, users_and_flair, parent_sub, sub_rules['sentiment'])
		karma_stats = hist_info.pop(0)
		sent_flair = hist_info.pop(0)
		total_submis = hist_info.pop(0)
		if sent_flair == True:
			flair_count += 1

		if sub_rules['accnt_age'] == True:
			#flairs user for account < 1 yr.
			age_flair = analyzeUserAge(user, users_and_flair, parent_sub)
		else:
			age_flair = False
		if age_flair == True:
			flair_count += 1

		if sub_rules['total_karma'] == True:
			#flairs user for karma < 1k
			if user.karma > 1000:
				appendFlair(user, str(user.comment_karma) + ' karma', users_and_flair)
				flair_count += 1

		#if user has attribute 'New to crypto' then don't add karma breakdown
		if total_submis > 15:
			small = False
			#if there are 2+ flair attributes already then use condensed version
			if flair_count >= 2:
				small = True
			if sub_rules['karma_breakdown'] == True:
				analyzeUserKarma(user, karma_stats, small, users_and_flair, parent_sub)
		elif sub_rules['new'] == True:
			appendFlair(user, 'New to crypto', users_and_flair)
		updateDB(user, total_submis, parent_sub)

#sentiment analysis of expired_users
def analyzeUserHist(user, users_and_flair, parent_sub, sent_rule):
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
			count += 1
			if sent_rule == True:
				commentSent = analyzeText(comment.body)
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

	if sent_rule == True:
		#analyze sentiment statistics
		flaired = sentFlair(user, count, countPos, countNeg, totalNeg, totalPos, users_and_flair)
	else:
		flaired = False

	totalPost = postCount + count
	return [sub_counter, flaired, totalPost]

#flair new accounts
def analyzeUserAge(user, users_and_flair, parent_sub):
	username = str(user)
	userCreated = datetime.fromtimestamp(user.created)
	tdelta = relativedelta.relativedelta(current_time, userCreated)
	flaired = False
	#create flair with appropriate time breakdown
	if tdelta.years < 1:
		flaired = True
		if tdelta.months < 1:
			days = tdelta.days
			flairText = str(days)
			if days == 1:
				appendFlair(username, flairText + ' day old', users_and_flair)
			else:
				appendFlair(username, flairText + ' days old', users_and_flair)
		else:
			months = tdelta.months
			flairText = str(months)
			if months == 1:
				appendFlair(user, flairText + ' month old', users_and_flair)
			else:
				appendFlair(user, flairText + ' months old', users_and_flair)
	return flaired

def analyzeUserKarma(user, sub_counter, small, users_and_flair, parent_sub):
	abrev = sub_abrev[parent_sub.upper()]
	hold_flair = abrev + ': ' + str(sub_counter[abrev]) + ' karma'

	if small == True:
		neg_flair = False
		neg_score = 0
		neg_sub = ''
		for key, value in sub_counter.most_common():
			if value < -10 and value < neg_score and key != abrev:
				neg_score = value
				neg_sub = key
				neg_flair = True
		if neg_flair == True:
			hold_flair += ' ' + neg_sub + ': ' + str(neg_score) + ' karma'
			appendFlair(user, hold_flair, users_and_flair)
		else:
			for key, value in sub_counter.most_common(1):
				if value > 250 and key != abrev:
					hold_flair += ' ' + key + ': ' + str(value) + ' karma'
			appendFlair(user, hold_flair, users_and_flair)

	else:
		#Add flair for sub karma > 1k
		for key, value in sub_counter.most_common(2):
			if value > 250 and key != abrev:
				hold_flair += ' ' + key + ': ' + str(value) + ' karma'
		#Add flair for sub karma < -10
		for key, value in sub_counter.most_common():
			if value < -10 and key != abrev:
				hold_flair += ' ' + key + ': ' + str(value) + ' karma'
		appendFlair(user, hold_flair, users_and_flair)

#Calculate Positive/Negative score from passed values
def sentFlair(user, count, countPos, countNeg, totalNeg, totalPos, users_and_flair):
	username = str(user)
	flaired = False
	countSent = (countPos + countNeg)
	#Require at least 20 comments for accurate analysis
	if count > 20 and countSent > 10:
		sentPerc = (countSent / float(count)) * 100
		#Require at least 7.5% of comments to show obvious sentiment
		if sentPerc < 7.5:
			print ('\t' + username + ': Not enough sentiment ' + str(sentPerc)[:4] + '% Count: ' + str(count) + ' CountSent: ' + str(countSent))
			return flaired
		posPerc = (countPos/float(countSent)) * 100
		negPerc = (countNeg/float(countSent)) * 100
		diffPerc = posPerc - negPerc

		#If there are 20% more negative comments than positive then flair user as negative
		if diffPerc < -20:
			appendFlair(user, 'Negative', users_and_flair)
			print ('\t' + username + ': Negative ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4])
			flaired = True

		#If there are 35% more positive comments than negative then flair user as positive
		elif diffPerc > 35:
			appendFlair(user, 'Positive', users_and_flair)
			flaired = True
			print ('\t' + username + ': Positive ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4])

		else:
			print ('\t' + username + ': Unknown ' + str(diffPerc)[:4] + '% Count: ' + str(count) + ' Sent: ' + str(sentPerc)[:4] + ' CountSent: ' + str(countPos + countNeg))

	else:
		print ('\t' + username + ': Unknown% Count: ' + str(count) + ' CountSent: ' + str(countSent))
	return flaired

#Search PM's for new messages with the syntax '!whitelist /u/someuser and add someuser to the whitelist
def readPMs(parent_sub, whitelist):
	mods = subs_and_mods[parent_sub]

	messages = reddit.inbox.unread()
	for message in messages:
		if str(message.author) in mods:
			message_text = message.body.split()
			command = message_text.pop(0)

			if command == '!whitelist':
				username = message_text.pop(0)
				print ('Command: ' + command + ' ' + username)

				if username.startswith("/u/"):
					targetUser = username[3:]
				elif username.startswith("u/"):
					targetUser = username[2:]
				else:
					targetUser = username

				addWhitelist(targetUser, parent_sub, whitelist)
				message.reply('User: ' + targetUser + ' was successfully added to the whitelist')
				message.mark_read()
				print ('Message about: ' + targetUser + ' was accepted and marked read')

			if command == '!abrev':
				sub_name = message_text.pop(0)
				abrev = message_text.pop(0)

				if sub_name.startswith("/r/"):
					target_sub = sub_name[3:].upper()
				elif sub_name.startswith("r/"):
					target_sub = sub_name[2:].upper()
				else:
					target_sub = sub_name.upper()

				if target_sub in sub_abrev:
					message.reply('The subreddit: ' + sub_name + ' already exists in the database. I will review this manually when I see the PM in my inbox.')
				else:
					addAbrev(target_sub, abrev)
					message.reply('The subreddit: ' + sub_name + ' with the abbreviation: ' + abrev + ' was added to the database successfully!')
					message.mark_read()
		else:
			print ('Message was not accpeted and left unread')

#concatonate flair
def appendFlair(user, newFlair, users_and_flair):
	username = str(user)
	if username in users_and_flair:
		holdFlair = users_and_flair[username]
		holdFlair += ' | ' + newFlair
		users_and_flair.update( {username : holdFlair})
	else:
		users_and_flair[username] = newFlair

#assign flair to users
def flairUsers(users_and_flair, parent_sub):
	sub = reddit.subreddit(parent_sub)
	print ('\nUsers and corresponding flair:\n')
	for username in users_and_flair:
		user = setUser(username)
		user_css = (next(sub.flair(user))['flair_css_class'])
		flair = users_and_flair[username]
		
		#if 'New to crypto' in flair or 'old' in flair:
		#user_css = 
		
		sub.flair.set(user, flair, user_css)
		print (username + ': ' + flair)

#add users to database with flair
def updateDB(user, total_submis, parent_sub):
	username = str(user)
	flair_time = json_serial(current_time)
	userDB = TinyDB(subs_and_userDB[parent_sub] + '.json')
	userDB.insert({'username' : username, 'flair_age' : flair_time, 'submis_count': total_submis})

#Add a username to the whitelistDB
def addWhitelist(username, parent_sub, whitelist):
	whitelistDB = TinyDB(subs_and_whitelist[parent_sub] + '.json')
	whitelistDB.insert({'username' : username})
	whitelist.append(username)
	print (username + ' added to whitelist')

def addAbrev(sub_name, abrev):
	abrevDB.insert({'sub': sub_name, 'abrev': abrev})
	sub_abrev[sub_name] = abrev
	print ('Sub updated in sub_abrev and abrevDB: ' + sub_name + '\t' + abrev)

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
	except (prawcore.exceptions.NotFound, AttributeError):
		return False
	return True

#main method
#get command line args
command = sys.argv[1]
#continuously scrape subreddit and apply flair to new users
if command == 'auto':
	while True:
		for parent_sub in subs:
			print ('Scraping: ' + parent_sub)
			current_users = readUserDB(parent_sub)
			whitelist = readWhitelistDB(parent_sub)
			users_and_flair = {}

			readPMs(parent_sub, whitelist)
			expired = findExpiredUsers(parent_sub, 300, 100, current_users, whitelist)
			analyzeUsers(expired, users_and_flair, parent_sub)
			flairUsers(users_and_flair, parent_sub)
		print('Sleeping for 1 min')
		time.sleep(60)
else:
	parent_sub = sys.argv[2]
	#one sweep of max posts and comments
	if command == 'big':
		print ('Scraping: ' + parent_sub)
		current_users = readUserDB(parent_sub)
		whitelist = readWhitelistDB(parent_sub)
		users_and_flair = {}

		#readPMs(parent_sub, whitelist)
		expired = findExpiredUsers(parent_sub, None, None, current_users, whitelist)
		analyzeUsers(expired, users_and_flair, parent_sub)
		flairUsers(users_and_flair, parent_sub)
	#small sweep for testing or low activity subs
	elif command == 'small':
		print ('Scraping: ' + parent_sub)
		current_users = readUserDB(parent_sub)
		whitelist = readWhitelistDB(parent_sub)
		users_and_flair = {}

		#readPMs(parent_sub, whitelist)
		expired = findExpiredUsers(parent_sub, 10, 5, current_users, whitelist)
		analyzeUsers(expired, users_and_flair, parent_sub)
		flairUsers(users_and_flair, parent_sub)
	#manually apply flair to a user
	elif command == 'manual':
		current_users = readUserDB(parent_sub)
		whitelist = readWhitelistDB(parent_sub)
		users_and_flair = {}
		targetName = sys.argv[3]
		target = setUser(targetName)

		if target != None:
			target_list = [target]
			analyzeUsers(target_list, users_and_flair, parent_sub)
			flairUsers(users_and_flair, parent_sub)
	#manually add a user to the whitelist
	elif command == 'whitelist':
		current_users = readUserDB(parent_sub)
		whitelist = readWhitelistDB(parent_sub)
		users_and_flair = {}
		targetName = sys.argv[3]
		addWhitelist(targetName, parent_sub, whitelist)
	#clear all users flair in whitelist
	elif command == 'clear_whitelist':
		whitelist = readWhitelistDB(parent_sub)
		clearWhitelistFlair(parent_sub, whitelist)
	#print guide to command line arguments
	else:
		print ('No arg given. Better luck next time\nArgs:\n\tauto - scrape subs for expired users\n\tbig + subreddit - get all available comments and posts from a subreddit (only does one sweep)\n\tsmall + subreddit - gets 10 comments and 5 posts from a sub (only does one sweep)\n\tmanual + username - manually flair a specific user\n\twhitelist username - add a user to the whitelist')
