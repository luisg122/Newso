"""
This file is licensed under the terms of the Apache License, Version 2.0. See the LICENSE file in the root of this
repository for complete details.
"""

from html import escape
from xml.sax.xmlreader import AttributesImpl

from boilerpy3.document import TextDocument
from boilerpy3.parser import BoilerpipeHTMLParser


class AnotherBoilerPipeHTMLParser(BoilerpipeHTMLParser):
    def __init__(self) -> None:
        super(AnotherBoilerPipeHTMLParser, self).__init__()
    
    def error(self, message):
        pass
    
    def handle_starttag(self, tag, attributes) -> None:
        self.start_element(tag, AttributesImpl(dict(attributes)))


class HTMLBoilerpipeMarker:
    ALLOWED_ATTRIBUTES = ['class', 'href', 'src']
    TA_IGNORABLE_ELEMENTS = ['STYLE', 'SCRIPT', 'OPTION', 'NOSCRIPT', 'OBJECT', 'EMBED', 'APPLET', 'LINK', 'HEAD',
                             'SVG', 'SELECT', 'FORM']
    
    def __init__(self, remove_elements=None, allowed_attributes=None) -> None:
        self.TA_IGNORABLE_ELEMENTS = remove_elements or self.TA_IGNORABLE_ELEMENTS
        self.ALLOWED_ATTRIBUTES = allowed_attributes or self.ALLOWED_ATTRIBUTES
    
    def process(self, doc: TextDocument, is_: str) -> str:
        implementation = Implementation(self)
        implementation.process(doc, is_)
        return implementation.html


class Implementation(AnotherBoilerPipeHTMLParser):
    html = ""
    in_ignorable_element = 0
    character_element_idx = 0
    content_bit_set = set()
    
    def __init__(self, hl: HTMLBoilerpipeMarker) -> None:
        
        self.hl = hl
        super(Implementation, self).__init__()
    
    def _xml_encode(self, s: str) -> str:
        return escape(s)
    
    def process(self, doc: TextDocument, is_: str):
        for block in doc.text_blocks:
            if block.is_content:
                bs = block.contained_text_elements
                if bs:
                    self.content_bit_set = self.content_bit_set.union(bs)
        
        self.feed(is_)
    
    def end_document(self):
        pass
    
    def start_document(self):
        pass
    
    def start_element(self, q_name: str, atts: dict) -> None:
        if q_name.upper() in self.hl.TA_IGNORABLE_ELEMENTS:
            self.in_ignorable_element += 1
        
        if self.in_ignorable_element == 0:
            self.html += '<' + q_name
            
            if self.character_element_idx + 1 in self.content_bit_set:
                self.html += ' x-boilerpipe-marker'
            
            for attr_name, attr_value in atts.items():
                if attr_name not in self.hl.ALLOWED_ATTRIBUTES:
                    continue
                self.html += ' {0}=\"{1}\"'.format(attr_name, self._xml_encode(attr_value or ""))
            
            self.html += '>'
    
    def end_element(self, q_name: str) -> None:
        try:
            if self.in_ignorable_element == 0:
                self.html += "</%s>" % q_name
        finally:
            if q_name.upper() in self.hl.TA_IGNORABLE_ELEMENTS:
                self.in_ignorable_element -= 1
    
    def characters(self, ch: str) -> None:
        self.character_element_idx += 1
        if self.in_ignorable_element == 0:
            if self.character_element_idx not in self.content_bit_set:
                return
            
            self.html += self._xml_encode(str(ch))
