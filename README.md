# SentimentTool
A mod tool for Reddit that flairs users based on their sentiment and other attributes

This python script users praw to scrape comments and posts from a target subreddit. The current code is implemented for some cryptocurrency subreddits, but can easily be altered for other subs. It then analyzes users for the following attributes:
	
* Account age < 1 year
* Karma in parent sub
* Negative karma in listed subs
* High karma in listed subs
* Few number of comments in listed subs
* < 1,000 comment karma
* Overall positive or negative comments

The script uses NLTK to preform sentiment analysis of the users comment history. Here is the pseudo code for how it determines if a user is positve, negative, or neutral:

	if > 15% of users comments show obvious sentiment:
		if there are 20% more negative comments than positive:
			user is negative
		else if there are 35% more positive comments than negative:
			user is positive

There is lots of room for fine tuning at this part of the code but I think this works pretty well for the time being. Once the analysis is finished, the users are flaired for the criteria they met and thier information is logged in a database. A user's flair is reassesed every 7 days to avoid needless API calls.
