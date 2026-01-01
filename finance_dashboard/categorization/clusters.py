"""Description clustering for transaction reporting."""

import re

import pandas as pd


def _compile_cluster_rules(cluster_rules):
    """Compile cluster patterns into regex objects.

    Args:
        cluster_rules: Dict mapping cluster names to pattern lists

    Returns:
        list: List of (label, compiled_patterns) tuples
    """
    compiled = []
    for label, patterns in cluster_rules.items():
        label = str(label).strip()
        if not label:
            continue
        compiled_patterns = []
        for pattern in patterns:
            pattern = str(pattern).strip()
            if not pattern:
                continue
            escaped = re.escape(pattern)
            escaped = escaped.replace(r"\*", ".*")
            compiled_patterns.append(re.compile(escaped, re.IGNORECASE))
        if compiled_patterns:
            compiled.append((label, compiled_patterns))
    return compiled


def apply_description_clusters(descriptions, cluster_rules):
    """Apply clustering rules to transaction descriptions.

    Args:
        descriptions: Series of transaction descriptions
        cluster_rules: Dict mapping cluster names to pattern lists

    Returns:
        Series: Clustered descriptions (original if no match)
    """
    compiled_rules = _compile_cluster_rules(cluster_rules)
    if not compiled_rules:
        return descriptions

    def match_cluster(description):
        text = "" if pd.isna(description) else str(description)
        for label, patterns in compiled_rules:
            for regex in patterns:
                if regex.search(text):
                    return label
        return text

    return descriptions.apply(match_cluster)
