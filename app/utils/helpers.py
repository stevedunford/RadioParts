from flask import current_app
from pathlib import Path


def validate_tags(tag_list, max_length=100, max_tags=8):
    """Clean and validate tags.
    Args:
        tag_list: List of raw tag strings
        max_length: Max characters per tag
        max_tags: Max number of tags allowed
    Returns:
        List of cleaned, unique tags
    """
    return list({t.strip()[:max_length]
                for t in tag_list
                if t.strip()})[:max_tags]


def secure_filename_custom(filename):
    """Enhanced secure filename for vintage parts"""
    from werkzeug.utils import secure_filename
    base = secure_filename(filename)
    return f"{Path(base).stem[:50]}_{hash(filename)[:5]}{Path(base).suffix}"


def log_error(context, error):
    """Standardized error logging"""
    current_app.logger.error(f"{context} | Error: {str(error)}")