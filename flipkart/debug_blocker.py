def is_blocked(text):
    blockers = [
        "access denied",
        "something went wrong",
        "access to this page has been denied",
        "please ensure you are not using a proxy"
    ]
    low = (text or "").lower()
    for b in blockers:
        if b in low:
            print(f"MATCH: '{b}'")

with open("c:/Users/aadit/OneDrive/Desktop/scrappers/debug/search_office_chair_page1.html", "r", encoding="utf-8") as f:
    text = f.read()
    is_blocked(text)
