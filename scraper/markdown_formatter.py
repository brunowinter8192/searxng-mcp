# INFRASTRUCTURE
import re

BLOCK_TAGS = {'p', 'div', 'section', 'article', 'main', 'blockquote'}
HEADING_TAGS = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### ', 'h5': '##### ', 'h6': '###### '}
LIST_TAGS = {'ul', 'ol'}
MAX_CONTENT_LENGTH = 15000


# ORCHESTRATOR
def to_markdown(nodes: list) -> str:
    raw_markdown = convert_nodes_to_markdown(nodes)
    cleaned = clean_whitespace(raw_markdown)
    truncated = truncate_content(cleaned, MAX_CONTENT_LENGTH)
    return truncated


# FUNCTIONS

# Convert parsed nodes to markdown string
def convert_nodes_to_markdown(nodes: list) -> str:
    result = []
    list_stack = []
    link_href = None

    for node in nodes:
        if node["type"] == "start":
            tag = node["tag"]
            attrs = node.get("attrs", {})

            if tag in HEADING_TAGS:
                result.append("\n\n" + HEADING_TAGS[tag])
            elif tag == "p":
                result.append("\n\n")
            elif tag == "br":
                result.append("\n")
            elif tag == "strong" or tag == "b":
                result.append("**")
            elif tag == "em" or tag == "i":
                result.append("*")
            elif tag == "code":
                result.append("`")
            elif tag == "pre":
                result.append("\n\n```\n")
            elif tag == "a":
                link_href = attrs.get("href", "")
                result.append("[")
            elif tag == "img":
                alt = attrs.get("alt", "image")
                src = attrs.get("src", "")
                result.append(f"![{alt}]({src})")
            elif tag == "ul":
                list_stack.append("ul")
                result.append("\n")
            elif tag == "ol":
                list_stack.append("ol")
                result.append("\n")
            elif tag == "li":
                indent = "  " * (len(list_stack) - 1)
                if list_stack and list_stack[-1] == "ol":
                    result.append(f"{indent}1. ")
                else:
                    result.append(f"{indent}- ")
            elif tag == "blockquote":
                result.append("\n\n> ")
            elif tag in BLOCK_TAGS:
                result.append("\n\n")

        elif node["type"] == "end":
            tag = node["tag"]

            if tag in HEADING_TAGS:
                result.append("\n")
            elif tag == "strong" or tag == "b":
                result.append("**")
            elif tag == "em" or tag == "i":
                result.append("*")
            elif tag == "code":
                result.append("`")
            elif tag == "pre":
                result.append("\n```\n\n")
            elif tag == "a":
                result.append(f"]({link_href})")
                link_href = None
            elif tag == "li":
                result.append("\n")
            elif tag == "ul" or tag == "ol":
                if list_stack:
                    list_stack.pop()
                result.append("\n")
            elif tag in BLOCK_TAGS:
                result.append("\n")

        elif node["type"] == "text":
            result.append(node["content"])

        elif node["type"] == "self_closing":
            tag = node["tag"]
            attrs = node.get("attrs", {})

            if tag == "br":
                result.append("\n")
            elif tag == "img":
                alt = attrs.get("alt", "image")
                src = attrs.get("src", "")
                result.append(f"![{alt}]({src})")
            elif tag == "hr":
                result.append("\n\n---\n\n")

    return "".join(result)


# Remove excessive whitespace
def clean_whitespace(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n +', '\n', text)
    text = text.strip()
    return text


# Truncate content if too long
def truncate_content(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_length * 0.8:
        truncated = truncated[:last_newline]
    return truncated + "\n\n[Content truncated...]"
