import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path

# === Settings ===
base_url = "https://git.altlinux.org/beehive/logs/Sisyphus/x86_64/latest/error/"
output_dir = "Data/x86_64/error/"
max_links = 1000000  # Maximum number of links to process

def get_links(url):
    """Gets all log links from the main page"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for tr in soup.select("table.project_list tr"):
        a_tag = tr.find("a", class_="link")
        if a_tag and a_tag.get("href") != "..":
            link = base_url + a_tag["href"]
            links.append((a_tag["href"], link))
    return sorted(links[:max_links])  # Ensure links are sorted

def get_last_downloaded_file():
    """Returns the name of the last downloaded file (alphabetically)"""
    if not os.path.exists(output_dir):
        return None
    files = sorted(os.listdir(output_dir))
    return files[-1] if files else None

def download_log(href, url):
    """Downloads a log file and saves it to the Data directory"""
    response = requests.get(url)
    
    # Create a safe filename from the href
    filename = href.replace('/', '_')
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    return filepath

def main():
    # Ensure output directory exists
    Path(output_dir).mkdir(exist_ok=True)
    
    # Get the last downloaded file
    last_file = get_last_downloaded_file()
    if last_file:
        print(f"Found last downloaded file: {last_file}")
    else:
        print("No existing files found, starting from beginning")
    
    # Get all links
    print("Getting list of logs...")
    links = get_links(base_url)
    
    # Find the starting point
    start_index = 0
    if last_file:
        for i, (href, _) in enumerate(links):
            if href.replace('/', '_') == last_file:
                start_index = i + 1
                break
    
    # Download remaining logs
    total_remaining = len(links) - start_index
    print(f"Continuing with {total_remaining} remaining files")
    
    for i, (href, link) in enumerate(links[start_index:], 1):
        print(f"Downloading {i}/{total_remaining}: {href}")
        filepath = download_log(href, link)
        print(f"Saved to: {filepath}")

    print(f"\nDone! Downloaded {total_remaining} files.")
    print(f"All logs are in the {output_dir} directory.")

if __name__ == "__main__":
    main()

 