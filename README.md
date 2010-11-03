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

The code is almost entirely in main.py.

References
----------
- [Mixamail.com](http://www.mixamail.com/)
- [Blog post announcing the site](http://www.s-anand.net/blog/twitter-via-e-mail/)

Planned development
-------------------
- facebook@mixamail.com fetches Facebook feeds
- read@mixamail.com response with the [readability](http://lab.arc90.com/experiments/readability/) equivalent of a page
- D: <username> sends a direct message to username
- Upload pictures
- Search subscriptions
- modified retweets
- embedded profile images?
