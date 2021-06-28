# Local SERP

Google Search Engine Results Pages (SERP) in locally, no API key, no signup required


## Make sure the chromedriver and required package are installed

Required packages

```
selenium
selenium-wire
beautifulsoup4
lxml
```

Then run to ensure everything is working

```
python -m serp.google
```

### Example code

User must provide the search url as google have different forms of search parameters for different devices and portals.

By default it will force google to render results in *english*, if google decides to assign other languages some parsing will fail. This also affects the language which the knowledge graph is rendered, so for now this library try to normalize everything to english.

```
from serp.google import extract
import urllib

query = 'What is GDPR'

encode_query = urllib.parse.urlencode({'q': query, 'oq': query })
url = 'https://www.google.com/search?{}&aqs=chrome.0.69i59j0l8.940j0j9&sourceid=chrome&ie=UTF-8'.format(encode_query)
result = extract(query, url)

```


## Supported features

* Featured Snippet

* Knowledge Graph extraction

    - Accordion, Snippet, Attributes, Alternative search query, Images, Knowledge Graph Source

* Spelling fix

* Search stats : total results, time taken

* Organic results

    - title, link, snippet

* Questions and Answers

    - People also asked card

* Related searches

## Not supported features

* Video, News, Images

* Location spoofing : Chrome location mocking doesn't work for google search, maybe try mozilla driver instead?

## Usage

Useful for OSINT, knowledge graph extraction, co-occurance query research, data mining, machine readable google results.


## Other

[This is part of the cause to build a better search engine](https://theblackcat102.github.io/designing-a-simple-search-engine/)
