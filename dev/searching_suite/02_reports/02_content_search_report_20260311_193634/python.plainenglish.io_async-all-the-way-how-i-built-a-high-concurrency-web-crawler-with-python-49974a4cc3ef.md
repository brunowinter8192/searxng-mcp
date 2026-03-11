# Async All the Way: How I Built a High-Concurrency Web Crawler with ...
**URL:** https://python.plainenglish.io/async-all-the-way-how-i-built-a-high-concurrency-web-crawler-with-python-49974a4cc3ef
**Domain:** python.plainenglish.io
**Score:** 5.3
**Source:** scraped
**Query:** python async web scraping tutorial

---

[Sitemap](https://python.plainenglish.io/sitemap/sitemap.xml)
Follow publication
New Python content every day. Follow to join our 3.5M+ monthly readers.
Follow publication
Member-only story
# Async All the Way: How I Built a High-Concurrency Web Crawler with Python
Follow
4 min read Jun 13, 2025
Share
_An in-depth breakdown of using_` _aiohttp_`_,_`_asyncio_`_, and_` _BeautifulSoup_`_to scrape 10,000+ pages without melting my machine—or my mind._
Photo by [Luca Bravo](https://unsplash.com/@lucabravo?utm_source=medium&utm_medium=referral) on [Unsplash](https://unsplash.com/?utm_source=medium&utm_medium=referral)
I used to think web scraping was easy. Write a script, loop through some URLs, save the data. Done. But once I tried to scrape 10,000 pages in under an hour, I hit a wall.
That’s when I realized: **traditional synchronous code won’t cut it**. What I needed was **non-blocking concurrency**. That’s how this project started — a high-performance, modular, async web crawler built entirely in Python.
If you’re still using `requests` and `for` loops to scrape, buckle up. This article walks through the real-world architecture, async patterns, and error-handling decisions I made to build a web crawler that felt less like a script—and more like a service.
## 1. Why Async: The Problem With Requests-Based Crawling
Here’s how most people scrape the web:
```
import requestsfrom bs4 import BeautifulSoupdef scrape(url):    response = requests.get(url)    soup = BeautifulSoup(response.text, 'html.parser')    return soup.title.string
```

Run that for a few hundred URLs, and your script becomes a bottleneck. It waits for each HTTP response…
## 
Create an account to read the full story.
The author made this story available to Medium members only.If you’re new to Medium, create a new account to read this story on us.
Or, continue in mobile web
Already have an account? 
Follow
## [Published in Python in Plain English](https://python.plainenglish.io/?source=post_page---post_publication_info--49974a4cc3ef---------------------------------------)
[Last published 1 hour ago](https://python.plainenglish.io/7-python-problems-every-developer-eventually-faces-42cdfb44abc1?source=post_page---post_publication_info--49974a4cc3ef---------------------------------------)
New Python content every day. Follow to join our 3.5M+ monthly readers.
Follow
Follow
## [Written by Suleman Safdar](https://medium.com/@SulemanSafdar?source=post_page---post_author_info--49974a4cc3ef---------------------------------------)
Freelancer IT specialist web developer
Follow
## No responses yet
Write a response
Cancel
Respond
## More from Suleman Safdar and Python in Plain English
## [I Stopped Writing Prompts and Built an AI Employee Instead The day I chained tools together and my inbox started answering itself](https://medium.com/@SulemanSafdar/i-stopped-writing-prompts-and-built-an-ai-employee-instead-0286576dff46?source=post_page---author_recirc--49974a4cc3ef----0---------------------a15c17da_e69d_4b16_93f6_c843c394be11--------------)
Feb 13
[ A clap icon112 A response icon2 ](https://medium.com/@SulemanSafdar/i-stopped-writing-prompts-and-built-an-ai-employee-instead-0286576dff46?source=post_page---author_recirc--49974a4cc3ef----0---------------------a15c17da_e69d_4b16_93f6_c843c394be11--------------)
In
by
## [The Python Skills That Actually Get You Hired in 2026 (And How to Learn Them) Why “Knowing Python” Isn’t Enough Anymore](https://python.plainenglish.io/the-python-skills-that-actually-get-you-hired-in-2026-and-how-to-learn-them-0f0fc4eaf5e0?source=post_page---author_recirc--49974a4cc3ef----1---------------------a15c17da_e69d_4b16_93f6_c843c394be11--------------)
Feb 8
[ A clap icon780 A response icon26 ](https://python.plainenglish.io/the-python-skills-that-actually-get-you-hired-in-2026-and-how-to-learn-them-0f0fc4eaf5e0?source=post_page---author_recirc--49974a4cc3ef----1---------------------a15c17da_e69d_4b16_93f6_c843c394be11--------------)
In
by
## [9 Python Lib

[Content truncated...]