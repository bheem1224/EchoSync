"""Test the edition extraction logic"""
import re

def extract_edition_new(raw_title):
    """New approach: Find LAST keyword, work backwards to delimiter"""
    version_keywords = r"(?:Remix|Mix|Live|Demo|Remaster|Deluxe|Edit|Version|Acoustic|Instrumental|Bonus|Extended|Original)"
    
    # Find all matches of version keywords
    all_matches = list(re.finditer(rf"\b{version_keywords}\b", raw_title, re.IGNORECASE))
    
    if not all_matches:
        return None, raw_title
    
    # Use the LAST match (rightmost)
    last_match = all_matches[-1]
    keyword_pos = last_match.start()
    
    # Look backwards from keyword to find the delimiter
    prefix = raw_title[:keyword_pos]
    
    # Find the LAST delimiter before the keyword
    last_dash = prefix.rfind(' - ')
    last_paren = prefix.rfind('(')
    last_bracket = prefix.rfind('[')
    
    # Use the rightmost delimiter
    delimiter_pos = max(last_dash, last_paren, last_bracket)
    
    if delimiter_pos >= 0:
        # Extract from delimiter to end
        if last_dash == delimiter_pos:
            edition_start = delimiter_pos + 3  # Skip " - "
        else:
            edition_start = delimiter_pos + 1  # Skip '(' or '['
        
        edition_text = raw_title[edition_start:].strip()
        
        # Remove trailing closing brackets/parens
        edition_text = re.sub(r'[\)\]]\s*$', '', edition_text).strip()
        
        # Clean title is everything before the delimiter
        clean_title = raw_title[:delimiter_pos].strip()
        
        return edition_text, clean_title
    
    return None, raw_title


def test_cases():
    tests = [
        ("Sweet Dreams (Are Made of This) - 2005 Remaster", "2005 Remaster", "Sweet Dreams (Are Made of This)"),
        ("Shut Up and Dance (Live at SiriusXM)", "Live at SiriusXM", "Shut Up and Dance"),
        ("Song Title (Remix)", "Remix", "Song Title"),
        ("Song Title [2020 Remaster]", "2020 Remaster", "Song Title"),
        ("Song - Radio Edit", "Radio Edit", "Song"),
        ("Normal Song Title", None, "Normal Song Title"),
        ("Song (Original Mix)", "Original Mix", "Song"),
    ]
    
    print("Testing edition extraction:\n")
    for raw_title, expected_edition, expected_title in tests:
        edition, clean_title = extract_edition_new(raw_title)
        
        status_edition = "✓" if edition == expected_edition else "✗"
        status_title = "✓" if clean_title == expected_title else "✗"
        
        print(f"{status_edition} {status_title} Input: {raw_title}")
        print(f"  Edition: {edition!r} (expected: {expected_edition!r})")
        print(f"  Title:   {clean_title!r} (expected: {expected_title!r})")
        print()


if __name__ == "__main__":
    test_cases()
