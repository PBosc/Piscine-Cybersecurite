import os
import requests
import bs4
import argparse
from urllib.parse import urljoin

# Define the function to download images from a given URL
def download_images(url, save_path, max_depth, current_depth=0, visited=None):
    if current_depth > max_depth:
        return
    if visited is None:
        visited = set()
    if url in visited:
        return

    visited.add(url)
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we notice bad responses
    except requests.exceptions.RequestException as e:
        print(f"\x1b[1;31mError fetching {url}: {e} \x1b[0m")
        return

    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    image_tags = soup.find_all('img')

    os.makedirs(save_path, exist_ok=True)

    for img in image_tags:
        img_url = img.get('src')
        if not img_url:
            continue
        if not img_url.startswith('http'):
            img_url = urljoin(url, img_url)
        if not any(img_url.endswith(ext) for ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp']):
            continue
        try:
            img_response = requests.get(img_url)
            img_response.raise_for_status()  # Ensure we notice bad responses
        except requests.exceptions.RequestException as e:
            print(f"\x1b[1;31mError fetching {img_url}: {e}\x1b[0m")
            continue
        file_name = img_url.split('/')[-1]
        file_path = os.path.join(save_path, file_name)
        with open(file_path, 'wb') as file:
            file.write(img_response.content)
        print(f"\x1b[1;32mDownloaded {file_name} to {file_path}\x1b[0m")

    # If recursive flag is set, find all links and download images from them
    if recursive:
        link_tags = soup.find_all('a', href=True)
        for link in link_tags:
            next_url = urljoin(url, link['href'])
            download_images(next_url, save_path, max_depth, current_depth + 1, visited)

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Download images from a URL.')
parser.add_argument('URL', help='The URL to download images from')
parser.add_argument('-r', action='store_true', help='Recursively download images')
parser.add_argument('-l', type=int, default=5, help='Maximum depth level for recursive download')
parser.add_argument('-p', default='./data/', help='Path where the downloaded files will be saved')

args = parser.parse_args()

# Assign arguments to variables
url = args.URL
recursive = args.r
max_depth = args.l
save_path = args.p

# Start downloading images
download_images(url, save_path, max_depth)
