'''
This file has a public version of information that needs to be kept secret.
Copy this file into secret_config.py and fill in the details.
'''

twitter_params = {
    'consumer_key'      : 'your-consumer-key-here',
    'consumer_secret'   : 'your-consumer-secret-here',
    'callback_url'      : 'http://your-server-url/auth/twitter',
}

# Get your facebook app registered at http://developers.facebook.com/setup/
facebook_params = {
    'app_id'        : 'your-facebook-app-id',
    'app_secret'    : 'your-facebook-app-secret',
}

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

# Get your anonymous imgur.com API key from http://imgur.com/register/api_anon
imgur_api = {
    'key': 'your-api-key',
}

# Admin accounts
sender_mail = 'applications-email-id@domain.com'
admins = [ 'your-user-id@domain.com' ]

# Type in a random 45+ character string and keep it a secret
cookie_secret = '12345678-9abc-def0-1234-567890abcdef-01234567-890a'
