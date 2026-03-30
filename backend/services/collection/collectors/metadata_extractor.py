"""Streaming JSON metadata extractor using ijson.

Extracts authors, file extensions, and item count from large JSON files
without loading the entire file into memory.
"""
import ijson
import logging

logger = logging.getLogger(__name__)


def extract_cleaning_metadata(stream, platform: str) -> dict:
    """
    Stream-parse a JSON file to extract cleaning metadata.

    Handles both formats:
    - Dict: {"merge_requests": [...]} or {"pull_requests": [...]}
    - List: [{...}, {...}, ...]

    Returns dict with authors, file_extensions, total_items.
    """
    authors = set()
    file_extensions = set()
    total_items = 0

    item_key = 'pull_requests' if platform == 'github' else 'merge_requests'

    # Peek at first byte to determine format
    first_byte = b''
    while True:
        b = stream.read(1)
        if not b:
            return _build_result(authors, file_extensions, total_items)
        if b in (b' ', b'\n', b'\r', b'\t', b'\xef', b'\xbb', b'\xbf'):
            continue
        first_byte = b
        break

    is_list_format = (first_byte == b'[')

    # Build a stream that replays the first byte
    replayed_stream = _ReplayStream(first_byte, stream)

    if is_list_format:
        prefix = 'item'
    else:
        prefix = f'{item_key}.item'

    try:
        for item in ijson.items(replayed_stream, prefix):
            total_items += 1

            # Extract author
            details = item.get('details', {}) or {}
            user = details.get('user') or {}
            author_info = details.get('author') or {}
            author = user.get('login') or author_info.get('username')
            if author:
                authors.add(author)

            # Extract file extensions
            files = item.get('files') or []
            for f in files:
                filename = f.get('filename') or f.get('new_path')
                if filename and '.' in filename:
                    ext = filename.rsplit('.', 1)[-1]
                    file_extensions.add(f'.{ext}')
    except Exception as e:
        logger.error(f"Error during streaming metadata extraction: {e}")

    return _build_result(authors, file_extensions, total_items)


def _build_result(authors, file_extensions, total_items):
    return {
        'authors': sorted(authors),
        'file_extensions': sorted(file_extensions),
        'total_items': total_items,
    }


class _ReplayStream:
    """Wraps a stream, prepending already-read bytes."""

    def __init__(self, prefix_bytes: bytes, stream):
        self._prefix = prefix_bytes
        self._prefix_offset = 0
        self._stream = stream

    def read(self, size=-1):
        if self._prefix_offset < len(self._prefix):
            remaining = self._prefix[self._prefix_offset:]
            if size < 0:
                self._prefix_offset = len(self._prefix)
                return remaining + self._stream.read()
            chunk = remaining[:size]
            self._prefix_offset += len(chunk)
            if len(chunk) < size:
                chunk += self._stream.read(size - len(chunk))
            return chunk
        return self._stream.read(size)
