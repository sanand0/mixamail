import os, os.path, re, urllib, datetime, logging, traceback, oauth
from email.utils import parseaddr, getaddresses, formataddr
from django.utils import simplejson as json
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import mail, urlfetch
from google.appengine.api.labs import taskqueue
from lilcookies import LilCookies   # Stores logged-in user's name via secure cookies
from utils import shrink, extend

try: import secret_config as config
except: import config

# Register your Twitter application at http://dev.twitter.com and fill these in
client = oauth.TwitterClient(**config.twitter_params)

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
    subscribe = db.IntegerProperty()    # Hour (GMT) to mail user. None if usubscribed
    last_id   = db.IntegerProperty()    # Last Twitter ID e-mailed to this e-mail
    last_fetch= db.DateTimeProperty()   # Time of last fetch (not record updation)


class HomePage(webapp.RequestHandler):
    def get(self):
        '''Displays the setup page for logged-in users, and home page for others.'''
        self.cookie = LilCookies(self, config.cookie_secret)
        username = self.cookie.get_secure_cookie('username')
        if not username:
            self.response.out.write(template.render('template/home.html', locals()))
        else:
            user = User.get_by_key_name(username)
            emails = Email.all().filter('username =', username)
            self.response.out.write(template.render('template/setup.html', locals()))

    def post(self):
        '''Adds or deletes e-mail addresses for a logged-in user'''
        self.cookie = LilCookies(self, config.cookie_secret)
        username = self.cookie.get_secure_cookie('username')
        email = self.request.get('email').lower()
        delete = self.request.get('delete').lower()
        if username:
            if email:
                mapping = Email.get_by_key_name(email) or Email(key_name=email)
                mapping.username = self.cookie.get_secure_cookie('username')
                mapping.subscribe = datetime.datetime.utcnow().hour
                mapping.put()
            elif delete:
                mapping = Email.get_by_key_name(delete)
                if mapping: mapping.delete()

        self.redirect('/')


class AuthPage(webapp.RequestHandler):
    '''Handles Twitter OAuth. See oauth.py for more documentation'''
    def get(self):
        self.cookie = LilCookies(self, config.cookie_secret)

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

class SubscriptionPage(webapp.RequestHandler):
    def get(self):
        '''Add all emails for current hour not fetched in the last hour'''
        now = datetime.datetime.utcnow()
        q = Email.all().filter('subscribe =', now.hour)
        q = q.filter('last_fetch <', now - datetime.timedelta(hours=1))
        ids = set(item.key().name() for item in q)
        logging.debug('Subscriptions queued: ' + repr(ids))
        tasks = [taskqueue.Task(url='/subscription', params={'id':id})
                 for id in ids]

        # Add in batches -- 100 is the limit
        queue = taskqueue.Queue('subscription')
        batch_size = 100
        for num in xrange(0, len(tasks), batch_size):
          try:
            queue.add(tasks[num:num+batch_size])
          except taskqueue.TaskAlreadyExistsError, taskqueue.DuplicateTaskNameError:
            pass

    def post(self):
        '''Fetch e-mail for a single user'''
        id = self.request.get('id')
        msg = mail.EmailMessage(sender=id, to=config.sender_mail, subject='Fetch')
        MailPage().receive(msg)


class LogoutPage(webapp.RequestHandler):
    '''Logs the user out by removing the cookie.'''
    def get(self):
        self.cookie = LilCookies(self, config.cookie_secret)
        self.redirect('/')


class MailPage(InboundMailHandler):
    '''Handles e-mail traffic'''

    def parse_cmd(self, message):
        '''Returns (command, param, body) where (command, param) is from subject,
        body is the first line in the body.'''
        try: subject = message.subject
        except: subject = ''

        cmd_re = re.compile(r'(\w+)[^a-z0-9_@]*(.*)', re.IGNORECASE)
        match = re.match(cmd_re, subject)
        if not match: return (None,None,None)
        command, param = match.groups()

        body = None
        for content_type, body in message.bodies(content_type='text/plain'):
            for line in body.decode().split('\n'):
                if line.strip():
                    body = line.strip()
                    break
            if body: break

        return command.lower(), param.strip(), body

    def receive(self, message):
        '''Depending on the subject, perform the appropriate action'''
        self.message = message
        self.from_name, self.from_mail = parseaddr(message.sender)
        self.mapping = Email.get_by_key_name(self.from_mail.lower())
        if self.mapping and self.mapping.username:
            self.user = User.get_by_key_name(self.mapping.username)

        command, param, body = self.parse_cmd(message)
        try:
            if       command == 'search'        : self.search(param or body)
            elif self.mapping:
                if   command == 'update'        : self.update(param or body)
                elif command == 'reply'         : self.update(body, id=param)
                elif command == 're'            : self.update(body, id=param)
                elif command == 'retweet'       : self.retweet(body, id=param)
                elif command == 'rt'            : self.retweet(body, id=param)
                elif command == 'like'          : self.like(body, id=param)
                elif command == 'google'        : self.google(param or body)
                elif command == 'subscribe'     : self.subscribe()
                elif command == 'unsubscribe'   : self.unsubscribe()
                else                            : self.fetch()
            else                                : self.reply_template('unknown')
        except Exception, e:
            logging.info(traceback.format_exc(e))
            self.reply_template('error', exception = repr(e),
                error="Twitter didn't let us " + (command or 'fetch'))

    def reply_template(self, temp, **data):
        '''Send a reply based on a specified template, passing it optional data'''
        handler = self
        body = template.render('template/' + temp + '.txt', locals())
        html = template.render('template/' + temp + '.html', locals()) if \
                os.path.exists('template/' + temp + '.html') else None
        try: sub = self.message.subject
        except: sub = ''
        if not re.match(r're\W', sub, re.IGNORECASE): sub = 'Re: ' + sub

        to_list = [formataddr((name, email)) for name, email in
                    getaddresses([self.message.sender] + [self.message.to])
                    if not email.lower() == config.sender_mail.lower()]

        # Log the e-mail and intended output
        logging.info(repr([self.message.sender, to_list, sub, body,
          [x.decode() for c,x in self.message.bodies(content_type='text/plain')],
        ]))

        out = mail.EmailMessage(
            sender  = config.sender_mail,
            to      = to_list,
            subject = sub,
            body    = body)
        if html: out.html = html
        try: out.cc = self.message.cc
        except: pass
        if config.admins: out.bcc = config.admins
        out.send()

    def update(self, content, id=None):
        if not content: return
        params = { 'status': shrink(content, 140) }
        if id: params['in_reply_to_status_id'] = id
        response = client.make_request(
            'http://api.twitter.com/1/statuses/update.json',
            self.user.token, self.user.secret, protected=True, method=urlfetch.POST,
            additional_params = params)
        if response.status_code != 200: logging.debug(response.content)
        self.reply_template('timeline', feed=extend([json.loads(response.content)]))

    def retweet(self, content, id):
        if not id: return
        response = client.make_request(
            'http://api.twitter.com/1/statuses/retweet/%s.json' % id,
            self.user.token, self.user.secret, protected=True, method=urlfetch.POST)
        if response.status_code != 200: logging.debug(response.content)
        self.reply_template('timeline', feed=extend([json.loads(response.content)]))

    def like(self, content, id):
        if not id: return
        response = client.make_request(
            'http://api.twitter.com/1/favorites/create/%s.json' % id,
            self.user.token, self.user.secret, protected=True, method=urlfetch.POST)
        if response.status_code != 200: logging.debug(response.content)
        self.reply_template('timeline', feed=extend([json.loads(response.content)]))

    def fetch(self):
        params = { 'count': 50 }
        if self.mapping.last_id: params['since_id'] = self.mapping.last_id
        response = client.make_request(
            'http://api.twitter.com/1/statuses/home_timeline.json',
            self.user.token, self.user.secret, protected=True,
            additional_params = params)
        feed = extend(json.loads(response.content))
        self.reply_template('timeline', feed=feed)
        if len(feed) > 0:
            self.mapping.last_id = feed[0]['id']
            self.mapping.last_fetch = datetime.datetime.utcnow()
            self.mapping.put()

    def search(self, content):
        # Make an authorised search request where possible
        if self.mapping and self.mapping.username:
            logging.info('Secure search request')
            response = client.make_request(
                'http://search.twitter.com/search.json',
                self.user.token, self.user.secret, protected=True,
                additional_params = { 'q': content, 'rpp': 50, })
        else:
            response = client.make_request(
                'http://search.twitter.com/search.json',
                additional_params = { 'q': content, 'rpp': 50, })
        if response.status_code != 200: logging.debug(response.content)
        self.reply_template('timeline',
            feed=extend(json.loads(response.content)['results']))

    def subscribe(self):
        hour = datetime.datetime.utcnow().hour
        self.mapping.subscribe = hour
        self.mapping.put()
        self.reply_template('subscribe', hour=hour)

    def unsubscribe(self):
        self.mapping.subscribe = None
        self.mapping.put()
        self.reply_template('unsubscribe')

    def google(self, content):
        data = urlfetch.fetch('http://ajax.googleapis.com/ajax/services/search/web?' +
            urllib.urlencode({
                'q': content,
                'v': '1.0',
                # 'userip': TODO: get this from self.message, somehow
                'rsz': '8',
                'key': config.google_api['apiKey'],
            }), headers = {
                'Referer': config.google_api['domain'],
            })
        self.reply_template('google', feed=json.loads(data.content))


application = webapp.WSGIApplication([
    ('/',               HomePage),
    ('/auth',           AuthPage),
    ('/logout',         LogoutPage),
    ('/subscription',   SubscriptionPage),
    MailPage.mapping(),
], debug=(os.name=='nt'))

if __name__ == '__main__':
    webapp.util.run_wsgi_app(application)
