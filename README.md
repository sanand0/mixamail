Introduction
------------
This is the source for [Mixamail.com](http://www.mixamail.com/) -- an e-mail gateway to [Twitter](http://twitter.com/).

All access is controlled via emails to [twitter@mixamail.com](mailto:twitter@mixamail.com). The subject determines the action:

- *update* sets the status to the first line of the body
- *fetch* retrieves all new tweets from the friends' timeline (since your last e-mail)
- *re: <status>* replies to the status
- *rt: <status>* retweets the status
- *subscribe* acts like a daily *fetch*
- *unsubscribe* cancels *subscribe*

The code is almost entirely in main.py.

References
----------
- [Mixamail.com](http://www.mixamail.com/)
- [Blog post announcing the site](http://www.s-anand.net/blog/twitter-via-e-mail/)
