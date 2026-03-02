# INFRASTRUCTURE
SKIP_TAGS = {'aside', 'script', 'style', 'noscript', 'iframe', 'svg', 'nav', 'footer', 'header', 'title'}
CONTENT_TAGS = {'main', 'article', 'section', 'div', 'body'}


# ORCHESTRATOR
def filter_content(parsed: dict, profile: dict) -> list:
    nodes = parsed.get("nodes", [])
    filtered = remove_skip_tags(nodes)
    main_content = extract_main_content(filtered)
    nav_patterns = profile.get("nav_patterns", [])
    clean_content = remove_navigation_attributes(main_content, nav_patterns)
    skip_classes = profile.get("skip_table_classes", [])
    if skip_classes:
        clean_content = remove_skip_tables(clean_content, skip_classes)
    noise_urls = profile.get("noise_url_patterns", [])
    if noise_urls:
        clean_content = remove_noise_links(clean_content, noise_urls)
    noise_text = profile.get("noise_text_patterns", [])
    if noise_text:
        clean_content = remove_noise_text(clean_content, noise_text)
    return clean_content


# FUNCTIONS

# Remove navigation elements by attributes
def remove_navigation_attributes(nodes: list, nav_patterns: list) -> list:
    result = []
    skip_depth = 0
    current_skip_tag = None
    filterable_tags = {'div', 'section', 'aside', 'ul', 'ol', 'li', 'span', 'label', 'button', 'input', 'form'}

    for node in nodes:
        if node["type"] == "start" and node["tag"] in filterable_tags:
            attrs = node.get("attrs", {})
            class_attr = attrs.get("class", "").lower()
            id_attr = attrs.get("id", "").lower()
            role_attr = attrs.get("role", "").lower()

            should_skip = (
                role_attr in ['navigation', 'complementary', 'banner', 'tab', 'tablist', 'tabpanel'] or
                any(pattern in class_attr for pattern in nav_patterns) or
                any(pattern in id_attr for pattern in nav_patterns)
            )

            if should_skip:
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


# Remove nodes that belong to skip tags using stack-based tracking
def remove_skip_tags(nodes: list) -> list:
    result = []
    skip_stack = []

    for node in nodes:
        if node["type"] == "start" and node["tag"] in SKIP_TAGS:
            skip_stack.append(node["tag"])
            continue

        if node["type"] == "end" and len(skip_stack) > 0:
            if node["tag"] == skip_stack[-1]:
                skip_stack.pop()
            continue

        if len(skip_stack) == 0:
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


# Find index of first content tag with improved priority
def find_content_tag_start(nodes: list) -> int:
    for priority_tag in ['main', 'article', 'section']:
        for i, node in enumerate(nodes):
            if node["type"] == "start" and node["tag"] == priority_tag:
                attrs = node.get("attrs", {})
                class_attr = attrs.get("class", "").lower()
                id_attr = attrs.get("id", "").lower()

                if priority_tag in ['main', 'article']:
                    return i

                if 'content' in class_attr or 'content' in id_attr or 'main' in class_attr or 'article' in class_attr:
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


# Remove links that match noise URL patterns
def remove_noise_links(nodes: list, patterns: list) -> list:
    result = []
    skip_until_link_end = False

    for node in nodes:
        if node["type"] == "start" and node["tag"] == "a":
            href = node.get("attrs", {}).get("href", "")
            if any(pattern in href for pattern in patterns):
                skip_until_link_end = True
                continue

        if node["type"] == "end" and node["tag"] == "a":
            if skip_until_link_end:
                skip_until_link_end = False
                continue

        if not skip_until_link_end:
            result.append(node)

    return result


# Remove text nodes that match noise patterns
def remove_noise_text(nodes: list, patterns: list) -> list:
    result = []
    exact_matches = {'--', 'Share', 'Listen'}

    for node in nodes:
        if node["type"] == "text":
            content_lower = node["content"].lower()
            if any(pattern in content_lower for pattern in patterns):
                continue
            if node["content"] in exact_matches:
                continue

        result.append(node)

    return result


# Remove tables matching skip class patterns
def remove_skip_tables(nodes: list, skip_classes: list) -> list:
    result = []
    skip_depth = 0

    for node in nodes:
        if node["type"] == "start" and node["tag"] == "table":
            class_attr = node.get("attrs", {}).get("class", "").lower()
            if any(pattern in class_attr for pattern in skip_classes):
                skip_depth += 1
                continue

        if skip_depth > 0:
            if node["type"] == "start" and node["tag"] == "table":
                skip_depth += 1
            elif node["type"] == "end" and node["tag"] == "table":
                skip_depth -= 1
            continue

        result.append(node)

    return result
