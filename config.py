'''
This file has a public version of information that needs to be kept secret.
Copy this file into secret_config.py and fill in the details.
'''

import oauth

# Register your Twitter application at http://dev.twitter.com and fill these in
client = oauth.TwitterClient(
    consumer_key    = 'your-consumer-key-here',
    consumer_secret = 'your-consumer-secret-here',
    callback_url    = 'http://your-server-url/auth',
)

# Get your bit.ly API key at http://bit.ly/a/your_api_key
bitly = {
    'login': 'bit.ly-username',
    'apiKey': 'bit.ly-api-key',
}

# Get your Google AJAX search key at http://code.google.com/apis/loader/signup.html
google_api = {
    'domain': 'http://domain.com/',
    'apiKey': 'your-api-key',
}

# Admin accounts
sender_mail = 'applications-email-id@domain.com'
admins = [ 'your-user-id@domain.com' ]

# Type in a random 45+ character string and keep it a secret
cookie_secret = '12345678-9abc-def0-1234-567890abcdef-01234567-890a'
