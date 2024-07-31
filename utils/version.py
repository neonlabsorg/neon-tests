import re


def remove_heading_chars_till_first_digit(input_string: str) -> str:
    result = re.sub(r'^[^\d]*', '', input_string)
    return result


def tag_to_branch(tag: str) -> str:
    parts = tag.split('.')
    branch = '.'.join(parts[:-1]) + '.x'
    return branch
