"""
This file is licensed under the terms of the Apache License, Version 2.0. See the LICENSE file in the root of this
repository for complete details.
"""

import re
import urllib.error
import urllib.parse
import urllib.request
from logging import getLogger
from typing import Union

from boilerpy3 import filters, parser
from boilerpy3.document import TextDocument
from boilerpy3.filters import BoilerpipeFilter
from boilerpy3.marker import HTMLBoilerpipeMarker

logger = getLogger('boilerpy3')


class Extractor:
    """
    The base class of Extractors. Also provides some helper methods to quickly retrieve the text that remained after
    processing.
    """
    
    SCRIPT_REGEX = re.compile(r'<(?:script|SCRIPT)[^>]*>.*?</(?:script|SCRIPT)>', re.DOTALL)
    
    def __init__(self, filtr: BoilerpipeFilter) -> None:
        self.filter = filtr
    
    def get_content(self, text: str) -> str:
        return self.get_doc(text).content
    
    def get_content_from_url(self, url: str) -> str:
        return self.get_doc_from_url(url).content
    
    def get_content_from_file(self, filename) -> str:
        return self.get_doc_from_file(filename).content
    
    def get_doc_from_file(self, filename) -> TextDocument:
        return self.get_doc(self.read_from_file(filename))
    
    def get_doc_from_url(self, url) -> TextDocument:
        return self.get_doc(self.read_from_url(url))
    
    def get_doc(self, text) -> TextDocument:
        doc = self.parse_doc(text)
        self.filter.process(doc)
        return doc
    
    def get_marked_html(self, text) -> str:
        doc = self.get_doc(text)
        m = HTMLBoilerpipeMarker()
        return m.process(doc, text)
    
    def read_from_file(self, filename: str) -> str:
        with open(filename) as text_file:
            return text_file.read()
    
    def read_from_url(self, url: str) -> str:
        with urllib.request.urlopen(url) as url_obj:
            text = url_obj.read()
            encoding = self.get_url_encoding(url_obj)
        
        try:
            text = text.decode(encoding)
        except UnicodeDecodeError:
            pass
        return text
    
    def get_url_encoding(self, f) -> str:
        try:
            return f.headers['content-type'].split('charset=')[1].split(';')[0]
        except:
            return 'utf8'
    
    def parse_doc(self, input_str: str) -> Union[TextDocument, None]:
        bp_parser = parser.BoilerpipeHTMLParser()
        try:
            bp_parser.feed(input_str)
        except:
            # in case of error, try again, first removing script tag content
            bp_parser = parser.BoilerpipeHTMLParser()
            input_str = self.SCRIPT_REGEX.sub('<script></script>', input_str)
            try:
                bp_parser.feed(input_str)
            except Exception:
                logger.exception('Error parsing HTML')
                return None
        doc = bp_parser.to_text_document()
        return doc


class DefaultExtractor(Extractor):
    """
    Usually worse than ArticleExtractor, but simpler/no heuristics. A quite generic full-text extractor.
    """
    
    _filter_chain = filters.FilterChain([
        filters.SimpleBlockFusionProcessor(),
        filters.BlockProximityFusion(1, False, False),
        filters.DensityRulesClassifier()
    ])
    
    def __init__(self):
        super().__init__(self._filter_chain)


class ArticleExtractor(Extractor):
    """
    A full-text extractor which is tuned towards news articles. In this scenario it achieves higher accuracy than
    DefaultExtractor. Works very well for most types of Article-like HTML.
    """
    
    _filter_chain = filters.FilterChain([
        filters.TerminatingBlocksFinder(),
        filters.DocumentTitleMatchClassifier(None, True),
        filters.NumWordsRulesClassifier(),
        filters.IgnoreBlocksAfterContentFilter(),
        filters.BlockProximityFusion(1, False, False),
        filters.BoilerplateBlockFilter(),
        filters.BlockProximityFusion(1, True, False),
        filters.KeepLargestBlockFilter(),
        filters.ExpandTitleToContentFilter()
    ])
    
    def __init__(self):
        super().__init__(self._filter_chain)


class LargestContentExtractor(Extractor):
    """
    A full-text extractor which extracts the largest text component of a page. For news articles, it may perform better
    than the DefaultExtractor, but usually worse than ArticleExtractor. Like DefaultExtractor, but keeps the largest
    text block only.
    """
    
    _filter_chain = filters.FilterChain([
        filters.NumWordsRulesClassifier(),
        filters.BlockProximityFusion(1, False, False),
        filters.KeepLargestBlockFilter()
    ])
    
    def __init__(self):
        super().__init__(self._filter_chain)


class CanolaExtractor(Extractor):
    """
    Trained on krdwrd Canola (different definition of "boilerplate"). You may give it a try.
    """
    
    _filter = filters.CanolaFilter()
    
    def __init__(self):
        super().__init__(self._filter)


class KeepEverythingExtractor(Extractor):
    """
    Marks everything as content. Dummy Extractor; should return the input text. Use this to double-check that your
    problem is within a particular BoilerpipeExtractor, or somewhere else.
    """
    
    _filter = filters.MarkEverythingContentFilter()
    
    def __init__(self):
        super().__init__(self._filter)


class NumWordsRulesExtractor(Extractor):
    """
    A quite generic full-text extractor solely based upon the number of words per block (the current, the previous and
    the next block).
    """
    
    _filter = filters.NumWordsRulesClassifier()
    
    def __init__(self):
        super().__init__(self._filter)


class ArticleSentencesExtractor(Extractor):
    """
    A full-text extractor which is tuned towards extracting sentences from news articles.
    """
    
    _filter_chain = filters.FilterChain([
        ArticleExtractor._filter_chain,
        filters.SplitParagraphBlocksFilter(),
        filters.MinClauseWordsFilter()
    ])
    
    def __init__(self):
        super().__init__(self._filter_chain)


class KeepEverythingWithMinKWordsFilter(filters.FilterChain):
    """
    A full-text extractor which extracts the largest text component of a page. For news articles, it may perform better
    than the DefaultExtractor, but usually worse than ArticleExtractor.
    """
    
    def __init__(self, k_min: int) -> None:
        # Note: variable was not used initially, seems it should be passed to super() call
        filter_arr = [
            filters.SimpleBlockFusionProcessor(),
            filters.MarkEverythingContentFilter(),
            filters.MinWordsFilter(k_min)
        ]
        super().__init__(filter_arr)
