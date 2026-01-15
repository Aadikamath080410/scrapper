from bs4 import BeautifulSoup
import os

def test():
    path = "c:/Users/aadit/OneDrive/Desktop/scrappers/debug/search_office_chair_page1.html"
    if not os.path.exists(path):
        print("File not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    print(f"Soup title: {soup.title.string if soup.title else 'No title'}")

    divs = soup.select("div[data-id]")
    print(f"Found {len(divs)} divs with data-id")
    
    for i, div in enumerate(divs[:3]):
        pid = div.get("data-id")
        print(f"Div {i} data-id: {pid}")
        a = div.select_one("a")
        if a:
            print(f"  Href: {a.get('href')}")
        else:
            print("  No anchor found")

if __name__ == "__main__":
    test()
