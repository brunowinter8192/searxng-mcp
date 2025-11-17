# INFRASTRUCTURE
from html.parser import HTMLParser
from html import unescape


# ORCHESTRATOR
def parse_html(html: str) -> dict:
    parser = HTMLContentParser()
    parser.feed(html)
    return parser.get_result()


# FUNCTIONS

# HTMLParser subclass that builds structured representation
class HTMLContentParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.result = []
        self.tag_stack = []
        self.current_attrs = {}

    # Handle opening tags
    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        self.current_attrs[tag] = dict(attrs)
        self.result.append({
            "type": "start",
            "tag": tag,
            "attrs": dict(attrs)
        })

    # Handle closing tags
    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        self.result.append({
            "type": "end",
            "tag": tag
        })

    # Handle text content between tags
    def handle_data(self, data):
        text = unescape(data.strip())
        if text:
            self.result.append({
                "type": "text",
                "content": text,
                "parent_tags": list(self.tag_stack)
            })

    # Handle self-closing tags
    def handle_startendtag(self, tag, attrs):
        self.result.append({
            "type": "self_closing",
            "tag": tag,
            "attrs": dict(attrs)
        })

    # Return parsed structure
    def get_result(self) -> dict:
        return {
            "nodes": self.result,
            "tag_stack": self.tag_stack
        }
