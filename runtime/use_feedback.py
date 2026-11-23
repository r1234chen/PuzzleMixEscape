import re

def reference(value, fallback):
    text = ' '.join(str(value or '').split())
    if not text or re.fullmatch('(?:s[123]_.+|R\\d+|L\\d+-\\d+|H1-\\d+)', text):
        return fallback
    text = re.sub('#\\d+\\s*', '', text).strip()
    if not text:
        return fallback
    return text if text.lower().startswith(('the ', 'this ', 'that ', 'your ')) else 'the ' + text

def rejection(item=None, target=None):
    return 'You cannot use ' + reference(item, 'this item') + ' on ' + reference(target, 'this object') + '.'
