'''
shrink(text, size): shrinks text to size, using URL shortening, word substitution, etc.
extend(feed): extends feed with more attributes
'''
import re, urllib, logging
try: import secret_config as config
except: import config

def re_compile(words):
    return dict((re.compile(k, re.IGNORECASE), v) for k,v in words.iteritems())

zapwords = re_compile({
  r'\b(a|an|the)\b': '',
})

words = re_compile({
  r'\byou': 'u',
  r'\band\b': '&',
  r'\bat\b': '@',
  r'\bare\b': 'R',
  r'\bpercent': '%',
  r'\b(sh|c|w)ould\b': r'\1d',
})

numbers = re_compile({
  r'\bzero\b'   : '0',
  r'one'        : '1',
  r'to+\b'      : '2',
  r'three'      : '3',
  r'fore?'      : '4',
  r'\bfive\b'   : '5',
  r'\bsix\b'    : '6',
  r'\bseven\b'  : '7',
  r'ate\b'      : '8',
  r'\bnine\b'   : '9',
})

punctuation = re_compile({
  r'[,;:"]' : ' ',
})



URL_RE = r'(\S+://\S+)'
def substitute(text, translate):
    if re.match(URL_RE, text): return text
    for source, target in translate.iteritems():
        text = re.sub(source, target, text, re.I)
    return text

VOWELS = re.compile(r'([b-df-hj-np-tv-z])[aeiou]+([b-df-hj-np-tv-z])', re.IGNORECASE)
def no_vowels_in_middle(text):
    if re.match(URL_RE, text): return text
    return re.sub(VOWELS, r'\1\2', text)

def no_punctuation_spaces(text):
    return re.sub(r' ?([^a-zA-Z0-9]) ?', r'\1', text)

def no_whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()

def short_url(text):
    if not re.match(URL_RE, text): return text
    return urllib.urlopen('http://api.bit.ly/v3/shorten', urllib.urlencode({
        'login': config.bitly['login'],
        'apiKey': config.bitly['apiKey'],
        'longUrl': text,
        'format': 'txt',
        'domain': 'j.mp',   # Shorter than bit.ly
    })).read()

def sizes(parts):
    return sum(len(x) for x in parts)


def shrink(text, size):
    '''This is the main function that shrinks tweets'''
    parts = re.split(URL_RE, text)

    if sizes(parts) > size: parts = [no_whitespace(x)           for x in parts]
    if sizes(parts) > size: parts = [short_url(x)               for x in parts]
    if sizes(parts) > size: parts = [substitute(x, words)       for x in parts]
    if sizes(parts) > size: parts = [substitute(x, zapwords)    for x in parts]
    if sizes(parts) > size: parts = [substitute(x, punctuation) for x in parts]
    if sizes(parts) > size: parts = [substitute(x, numbers)     for x in parts]
    if sizes(parts) > size: parts = [no_punctuation_spaces(x)   for x in parts]
    if sizes(parts) > size: parts = [no_vowels_in_middle(x)     for x in parts]

    return no_whitespace(' '.join(parts))[:size]


import rfc822, time, datetime
from ttp import Parser as TwitterParser

def unicodize(object):
    '''Django 0.96 template tags (like firstof) don't support unicode.
    This function does a deep conversion of every string to UTF-8'''
    t = type(object)
    if t is unicode:
        object = object.encode('utf-8')
    elif t is list:
        for i, v in enumerate(object): object[i] = unicodize(v)
    elif t is dict:
        for i, v in object.iteritems(): object[i] = unicodize(v)
    return object

def extend(feed):
    now = time.time()
    parser = TwitterParser(config.sender_mail, max_url_length=140)
    for entry in feed:
        if isintance(entry, str):
            logging.error('Entry is not a dict, but is a string: ' + entry)
            logging.error('Feed is: ' + repr(feed))
            break

        # Add ['ago'] as the relative date
        t = rfc822.parsedate(entry['created_at'])
        d = now - time.mktime(t)
        if   d < 90     : entry['ago'] = '%.0fsec' % d
        elif d < 5400   : entry['ago'] = '%.0fmin' % (d/60)
        elif d < 129600 : entry['ago'] = '%.0fhr' % (d/3600)
        else            : entry['ago'] = datetime.datetime(*t[:6]).strftime('%d-%b')

        # Add ['html'] as the html version of the text
        entry['html'] = parser.parse(entry['text']).html

    return unicodize(feed)
