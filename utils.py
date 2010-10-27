'''
shrink(text, size): shrinks text to size, using URL shortening, word substitution, etc.
'''
import re, urllib
try: from secret_config import bitly
except: from config import cookie_secret, client

def re_compile(words):
    return dict((re.compile(k, re.IGNORECASE), v) for k,v in words.iteritems())

zapwords = re_compile({
  r'\b(a|an|the)\b': '',
})

words = re_compile({
  r'\byou\b': 'u',
  r'\byour\b': 'ur',
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
        'login': bitly['login'],
        'apiKey': bitly['apiKey'],
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
