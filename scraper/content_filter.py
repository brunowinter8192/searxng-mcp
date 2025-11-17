# INFRASTRUCTURE
SKIP_TAGS = {'nav', 'footer', 'header', 'aside', 'script', 'style', 'noscript', 'iframe', 'svg'}
CONTENT_TAGS = {'main', 'article', 'section', 'div', 'body'}
INLINE_TAGS = {'a', 'strong', 'b', 'em', 'i', 'code', 'span', 'img'}


# ORCHESTRATOR
def filter_content(parsed: dict) -> list:
    nodes = parsed.get("nodes", [])
    filtered = remove_skip_tags(nodes)
    main_content = extract_main_content(filtered)
    return main_content


# FUNCTIONS

# Remove nodes that belong to skip tags
def remove_skip_tags(nodes: list) -> list:
    result = []
    skip_depth = 0
    current_skip_tag = None

    for node in nodes:
        if node["type"] == "start" and node["tag"] in SKIP_TAGS:
            if skip_depth == 0:
                current_skip_tag = node["tag"]
            skip_depth += 1
            continue

        if node["type"] == "end" and skip_depth > 0:
            if node["tag"] == current_skip_tag:
                skip_depth -= 1
                if skip_depth == 0:
                    current_skip_tag = None
            continue

        if skip_depth == 0:
            result.append(node)

    return result


# Extract content from main/article tags or return all
def extract_main_content(nodes: list) -> list:
    main_start = find_content_tag_start(nodes)
    if main_start == -1:
        return nodes

    main_end = find_matching_end(nodes, main_start)
    if main_end == -1:
        return nodes

    return nodes[main_start:main_end + 1]


# Find index of first content tag
def find_content_tag_start(nodes: list) -> int:
    for priority_tag in ['main', 'article']:
        for i, node in enumerate(nodes):
            if node["type"] == "start" and node["tag"] == priority_tag:
                return i
    return -1


# Find matching end tag index
def find_matching_end(nodes: list, start_idx: int) -> int:
    if start_idx == -1:
        return -1

    tag = nodes[start_idx]["tag"]
    depth = 1

    for i in range(start_idx + 1, len(nodes)):
        node = nodes[i]
        if node["type"] == "start" and node["tag"] == tag:
            depth += 1
        elif node["type"] == "end" and node["tag"] == tag:
            depth -= 1
            if depth == 0:
                return i

    return -1
