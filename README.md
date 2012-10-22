NOTE: Mixamail.com will be shut down on Thu 25 Oct, 2012. See http://s-anand.net/mixamail.html

Introduction
------------
This is the source for [Mixamail.com](http://www.mixamail.com/) -- an e-mail gateway to [Twitter](http://twitter.com/).

All access is controlled via emails to [twitter@mixamail.com](mailto:twitter@mixamail.com). The subject determines the action:

- *update* sets the status to the first line of the body
- *fetch* retrieves all new tweets from the friends' timeline (since your last e-mail)
- *re: <status>* replies to the status
- *rt: <status>* retweets the status
- *like: <status>* favorites the status
- *subscribe* acts like a daily *fetch* at the time the mail is sent
- *unsubscribe* cancels *subscribe*
- *google <search-terms>* searches for search terms

The code is almost entirely in main.py.

References
----------
- [Mixamail.com](http://www.mixamail.com/)
- [Blog post announcing the site](http://www.s-anand.net/blog/twitter-via-e-mail/)
- [Blog post announcing Google search](http://www.s-anand.net/blog/google-search-via-e-mail/)

Planned development (inactive)
-------------------
- facebook@mixamail.com fetches Facebook feeds
- read@mixamail.com response with the [readability](http://lab.arc90.com/experiments/readability/) equivalent of a page
- D: <username> sends a direct message to username
- Search subscriptions
- modified retweets
- embedded profile images?
