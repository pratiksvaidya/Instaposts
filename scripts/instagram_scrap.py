import pickle
from google.cloud import firestore
from bs4 import BeautifulSoup
import selenium.webdriver as webdriver
import sys
import dateutil.parser
import time

db = firestore.Client()

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('headless')

hashtag = sys.argv[1]

### Save records to file

col_ref = db.collection(u'insta-posts')
entries = col_ref.get()

records = dict()
for entry in entries:
    records[entry.id]=entry.to_dict()

records_f = open("records.pkl","wb")
pickle.dump(records,records_f)
records_f.close()

## Check for new posts with #VenturingBSA
print('#' + hashtag)
url = 'https://www.instagram.com/explore/tags/' + hashtag + '/'
driver = webdriver.Chrome(chrome_options=chrome_options)
driver.get(url)

posts = set()

SCROLL_PAUSE_TIME = 5
# Get scroll height
last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    # Scroll down to bottom
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    # Wait to load page
    time.sleep(SCROLL_PAUSE_TIME)
    # Calculate new scroll height and compare with last scroll height
    new_height = driver.execute_script("return document.body.scrollHeight")
    soup = BeautifulSoup(driver.page_source, features='html.parser')
    images = soup.findAll('img')
    header = soup.find('h2', text = 'Most recent')
    if header == None:
        header = soup.find('header')
        links = header.find_next_sibling('article').findAll('a')
    else:
        links = header.find_next_sibling('div').findAll('a')

    for link in links:
        if link['href'].split('/')[2] in records:
            up_to_date = True
        else:
            up_to_date = False
            posts.add('https://www.instagram.com'+link['href'])
    if new_height == last_height or up_to_date:
        break
    last_height = new_height

driver.close()

posts = list(posts)

posts_f = open("posts_" + hashtag + ".pkl","wb")
pickle.dump(posts,posts_f)
posts_f.close()

### Get post information from each link

results = list()
for post in posts: 
    driver = webdriver.Chrome(chrome_options=chrome_options)
    driver.get(post)
    soup = BeautifulSoup(driver.page_source, features='html.parser')

    try: # Skips videos
        author = soup.find('div', { 'class' : 'C4VMK' }).find('a').text
        caption = soup.find('div', { 'class' : 'C4VMK' }).find('span').text
        likes = soup.find('span', { 'class' : 'zV_Nj' }).find('span').text
        image = soup.find('div', { 'class' : 'KL4Bh' }).find('img')['src']
        posted = soup.find('a', { 'class' : 'c-Yi7' }).find('time')['datetime']

        results.append({
            'url': post,
            'author': author,
            'caption': caption,
            'like_count': likes,
            'img_src': image,
            'posted_dt': dateutil.parser.parse(posted),
            'tags': [tag.strip("#") for tag in caption.split() if tag.startswith("#")]
        })
    except:
        pass
    driver.close()

results_f = open("results.pkl","wb")
pickle.dump(results,results_f)
results_f.close()

### Save results to Firebase Database
from google.cloud import firestore

for result in results:
    print(result['url'])
    col_ref = db.collection(u'insta-posts')
    doc_ref = col_ref.document(result['url'].split('/')[4])
    doc_ref.set({
        'author': result['author'],
        'caption': result['caption'],
        'img_src': result['img_src'],
        'like_count': int(result['like_count'].replace(',','')),
        'url': result['url'],
        'tags': result['tags'],
        'posted_dt': result['posted_dt'],
        'active': True,
        'approved': False
    })
print('Success!')