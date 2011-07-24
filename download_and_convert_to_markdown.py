#!/usr/bin/env python
#
# Downloads California Constitution from www.leginfo.ca.gov, and converts to Markdown.
#

import os
import re
import time
import urllib
import sys

import BeautifulSoup

CACHE_DIR = "calif_const_cache"

class Constitution (object):

    def __init__(self, preamble, articles):
        self.preamble = preamble
        self.articles = articles

    def as_markdown(self):
        parts = ["# Constitution of the State of California",self.preamble] \
              + [article.as_markdown() for article in self.articles]
        return "\n\n".join(parts)

class Article (object):

    def __init__(self, number, sections, name=None):
        self.number = number
        self.sections = sections
        self.name = name

    def as_markdown(self):
        header = "## Article %s" % self.number
        if self.name is not None:
            header += " (%s)" % self.name
        parts = [header] + [section.as_markdown() for section in self.sections]
        return "\n\n".join(parts)

class Section (object):

    def __init__(self, number, paragraphs):
        self.number = number
        self.paragraphs = paragraphs

    def as_markdown(self):
        parts = ["### Section %s" % self.number] + self.paragraphs
        return "\n\n".join(parts)

def get_url( url, ofn, max_attempts=10 ):
    for attempt in range(max_attempts):
        try:
            if attempt == 0:
                print "downloading %s" % url
            else:
                print "- failed, trying again"
            urllib.urlretrieve(url, ofn)
            return
        except IOError:
            pass
        time.sleep(5)
    raise Exception("failed to download %s" % url)

def readfile( filename ):
    f = open( filename )
    s = f.read()
    f.close()
    return s

def download_constitution(cache_dir):
    site = "http://www.leginfo.ca.gov/"
    toc_fn = os.path.join(cache_dir,"toc.html")
    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)
    get_url("http://www.leginfo.ca.gov/const-toc.html", toc_fn)
    toc = readfile(toc_fn)
    soup = BeautifulSoup.BeautifulSoup(toc)
    index = open(os.path.join(cache_dir,'index'), 'w')
    for a in soup.findAll('a', href=re.compile(r'^.const')):
        url = site + a['href']
        ofn = a['href'][8:] # strip off ^.const/.
        get_url(url, os.path.join(cache_dir,ofn))
        print >>index, ofn
    index.close()

def parse_constitution(cache_dir):
    fns = get_article_filenames(cache_dir)
    assert fns[0].endswith("preamble")
    preamble = parse_preamble(fns[0])
    articles = [parse_article(fn) for fn in fns[1:]]
    return Constitution(preamble, articles)

def get_article_filenames(cache_dir):
    article_fns = []
    ifn = os.path.join(cache_dir, 'index')
    for line in open(ifn):
        article_fns.append(os.path.join(cache_dir, line.strip()))
    return article_fns

def parse_preamble(fn):
    text = readfile(fn)
    text = re.sub(r"CALIFORNIA CONSTITUTION\nPREAMBLE", "", text)
    return text.strip()

def filter_blanks(strings):
    return [s for s in strings if len(s.strip()) > 0]

def parse_article(fn):
    number = fn.split('_')[-1]
    text = readfile(fn)
    text = re.sub(r"\r", "", text)
    # get article name
    pattern = r"^CALIFORNIA CONSTITUTION\nARTICLE %s  [(\[]?([\w,\- ]+)[)\]]?$" % number
    m = re.search(pattern, text, re.M)
    name = m.group(1).upper()
    # the weird "o?\n?" fixes bugs in articles 10 & 10B
    pattern = r"^o?\n?CALIFORNIA CONSTITUTION\nARTICLE %s  [ \S]+$" % number
    section_texts = filter_blanks(re.split(pattern, text, flags=re.M))
    sys.stdout.write("parsing %3s:" % number)
    sections = [parse_section(text) for text in section_texts]
    print
    return Article(number, sections, name=name)

def parse_section(text):
    text = text.strip()
    # some sections are [bracketed]; not sure why
    pattern = r"\[?(section|sec\.) ([\d./]+)\.\]? "
    m = re.match(pattern, text, re.I)
    try:
        number = m.group(2)
        if number.endswith("1/2"):
            oldnumber = number
            number = oldnumber.replace("1/2", ".5")
            sys.stdout.write(" %s -> %s" % (oldnumber,number))
        else:
            sys.stdout.write(" %s" % number)
        offset = len(m.group(0))
        return Section(number, parse_paragraphs(text[offset:]))
    except:
        print
        print text
        raise

def parse_paragraphs(text):
    paragraphs = re.split(r"^ ", text, flags=re.M)
    return [p.strip() for p in filter_blanks(paragraphs)]

if __name__ == '__main__':
    if not os.path.exists(CACHE_DIR):
        download_constitution(CACHE_DIR)
    constitution = parse_constitution(CACHE_DIR)
    f = open("README.md", 'w')
    print >>f, constitution.as_markdown()
    f.close()

