import os, os.path, re, datetime, logging
from email.utils import parseaddr
from django.utils import simplejson as json
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import mail, urlfetch
from lilcookies import LilCookies   # Stores logged-in user's name via secure cookies
from utils import shrink

try: from secret_config import cookie_secret, client
except: from config import cookie_secret, client

class User(db.Model):
    '''Holds the Twitter user's information. key_name = twitter username'''
    created = db.DateTimeProperty(auto_now=True)
    name    = db.StringProperty()   # Display name for the user
    picture = db.StringProperty()   # Profile image URL
    token   = db.StringProperty()   # OAuth token
    secret  = db.StringProperty()   # OAuth secret

class Email(db.Model):
    '''Maps email addresses to a Twitter username. key_name = email'''
    username  = db.StringProperty()     # Twitter userid authorised for the e-mail
    subscribe = db.IntegerProperty()    # Hour (GTM) to mail user. None if usubscribed
    last_id   = db.IntegerProperty()    # Last Twitter ID e-mailed to this e-mail
    last_fetch= db.DateTimeProperty(auto_now=True)


class HomePage(webapp.RequestHandler):
    def get(self):
        '''Displays the setup page for logged-in users, and home page for others.'''
        self.cookie = LilCookies(self, cookie_secret)
        username = self.cookie.get_secure_cookie('username')
        if not username:
            self.response.out.write(template.render('template/home.html', locals()))
        else:
            user = User.get_by_key_name(username)
            emails = Email.all().filter('username =', username)
            self.response.out.write(template.render('template/setup.html', locals()))

    def post(self):
        '''Adds or deletes e-mail addresses for a logged-in user'''
        self.cookie = LilCookies(self, cookie_secret)
        username = self.cookie.get_secure_cookie('username')
        email = self.request.get('email').lower()
        delete = self.request.get('delete').lower()
        if username:
            if email:
                mapping = Email.get_by_key_name(email) or Email(key_name=email)
                mapping.username = self.cookie.get_secure_cookie('username')
                mapping.put()
            elif delete:
                mapping = Email.get_by_key_name(delete)
                if mapping: mapping.delete()

        self.redirect('/')


class AuthPage(webapp.RequestHandler):
    '''Handles Twitter OAuth. See oauth.py for more documentation'''
    def get(self):
        self.cookie = LilCookies(self, cookie_secret)

        if self.request.get('oauth_token'):
            auth_token = self.request.get('oauth_token')
            auth_verifier = self.request.get('oauth_verifier')
            user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)

            username = user_info['username']
            user = User.get_by_key_name(username) or User(key_name=username)
            user.name    = user_info['name']
            user.picture = user_info['picture']
            user.token   = user_info['token']
            user.secret  = user_info['secret']
            user.put()

            self.cookie.set_secure_cookie('username', username)
            self.redirect('/')

        else:
            self.redirect(client.get_authorization_url())


class LogoutPage(webapp.RequestHandler):
    '''Logs the user out by removing the cookie.'''
    def get(self):
        self.cookie = LilCookies(self, cookie_secret)
        self.redirect('/')


class MailPage(InboundMailHandler):
    '''Handles e-mail traffic'''

    def receive(self, message):
        '''Depending on the subject, perform the appropriate action'''
        self.from_name, self.from_mail = parseaddr(message.sender)
        self.to_name, self.to_mail = parseaddr(message.to)
        self.mapping = Email.get_by_key_name(self.from_mail.lower())
        try: sub = message.subject
        except: sub = ''
        if self.mapping:
            if   re.match(r'update'             , sub, re.I): self.update     (message)
            elif re.match(r'retweet.*?(\d+)$'   , sub, re.I): self.retweet    (message)
            elif re.match(r'rt.*?(\d+)$'        , sub, re.I): self.retweet    (message)
            elif re.match(r're.*?(\d+)$'        , sub, re.I): self.update     (message)
            elif re.match(r'subscribe'          , sub, re.I): self.subscribe  (message)
            elif re.match(r'unsubscribe'        , sub, re.I): self.unsubscribe(message)
            elif sub: self.fetch(message)
        else: self.unknown(message)

    def reply_template(self, message, temp, **data):
        '''Send a reply based on a specified template, passing it optional data'''
        handler = self
        body = template.render('template/' + temp + '.txt', locals())
        html = template.render('template/' + temp + '.html', locals()) if \
                os.path.exists('template/' + temp + '.html') else None

        # Log the e-mail and intended output
        logging.info(repr([message.sender, message.to, message.subject, body,
          [x.decode() for c,x in message.bodies(content_type='text/plain')],
        ]))

        # Send the reply
        out         = mail.EmailMessage()
        out.sender  = 'twitter@mixamail.com'
        out.to      = message.sender
        out.subject = message.subject
        out.body    = body
        if html: out.html = html
        if not re.match(r're\W', out.subject, re.IGNORECASE):
            out.subject = 'Re: ' + out.subject
        try: out.cc = message.cc
        except: pass
        out.send()

    def unknown(self, message):
        '''Reply with an introductory message for unknown e-mail IDs'''
        self.reply_template(message, 'unknown')

    def update(self, message):
        '''Update user's status, or reply to an existing status'''
        user = User.get_by_key_name(self.mapping.username)
        body = None
        # Take the first non-empty line of the body
        for content_type, body in message.bodies(content_type='text/plain'):
            for line in body.decode().split('\n'):
                if line.strip():
                    body = line.strip()
                    break

        if not body: return

        params = { 'status': shrink(body, 140) }
        match = re.match(r're.*?(\d+)$', message.subject, re.I)
        if match: params['in_reply_to_status_id'] = match.group(1)

        try:
            response = client.make_request(
                'http://api.twitter.com/1/statuses/update.json',
                user.token, user.secret, protected=True, method=urlfetch.POST,
                additional_params=params)
            feed = json.loads(response.content)
            self.reply_template(message, 'timeline', feed=[feed])
        except Exception, e:
            self.reply_template(message, 'error', exception = repr(e),
                error="Twitter didn't let us send your tweet.")

    def retweet(self, message):
        '''Re-tweet a message'''
        user = User.get_by_key_name(self.mapping.username)
        match = re.match(r'rt.*?(\d+)$', message.subject, re.I)
        if not match: return
        try:
            response = client.make_request(
                'http://api.twitter.com/1/statuses/retweet/' + match.group(1) + '.json',
                user.token, user.secret, protected=True, method=urlfetch.POST)
            feed = json.loads(response.content)
            self.reply_template(message, 'timeline', feed=[feed])
        except Exception, e:
            self.reply_template(message, 'error', exception = repr(e),
                error="Twitter didn't let us retweet.")

    def fetch(self, message):
        '''Fetch messages since last e-mail'''
        user = User.get_by_key_name(self.mapping.username)
        params = { 'count': 50 }
        if self.mapping.last_id: params['since_id'] = self.mapping.last_id
        try:
            response = client.make_request(
                'http://api.twitter.com/1/statuses/friends_timeline.json',
                user.token, user.secret, protected=True,
                additional_params = params)
            feed = json.loads(response.content)
            self.reply_template(message, 'timeline', feed=feed)
            if len(feed) > 0:
                self.mapping.last_id = feed[0]['id']
                self.mapping.put()
        except Exception, e:
                self.reply_template(message, 'error', exception = repr(e),
                    error="Twitter didn't let us fetch your tweets.")

    def subscribe(self, message):
        hour = datetime.datetime.utcnow().hour
        self.mapping.subscribe = hour
        self.mapping.put()
        self.reply_template(message, 'subscribe', hour=hour)

    def unsubscribe(self, message):
        self.mapping.subscribe = None
        self.mapping.put()
        self.reply_template(message, 'unsubscribe')


# TODO: Cron job for subscribes


application = webapp.WSGIApplication([
    ('/',           HomePage),
    ('/auth',       AuthPage),
    ('/logout',     LogoutPage),
    MailPage.mapping(),
], debug=(os.name=='nt'))

if __name__ == '__main__':
    webapp.util.run_wsgi_app(application)
