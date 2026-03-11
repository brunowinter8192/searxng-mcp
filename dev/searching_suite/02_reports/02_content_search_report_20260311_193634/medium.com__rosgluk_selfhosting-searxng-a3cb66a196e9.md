# Selfhosting SearXNG - by Rost Glukhov - Medium
**URL:** https://medium.com/@rosgluk/selfhosting-searxng-a3cb66a196e9
**Domain:** medium.com
**Score:** 5.3
**Source:** scraped
**Query:** searxng configuration best practices

---

[Sitemap](https://medium.com/sitemap/sitemap.xml)
# Selfhosting SearXNG
Follow
6 min read Feb 11, 2025
Share
[SearXNG](https://www.glukhov.org/post/2025/02/selfhosting-searxng/) is a free and open-source federated metasearch engine that was forked from Searx. The [SearXNG project](https://github.com/searxng/searxng) on github has more then 15k stars.
It aggregates search results from over 70 different search engines and services, presenting them in a single, comprehensive list.
I realy loved how it works with perplexica (<https://www.glukhov.org/post/2024/08/selfhosting-perplexica-ollama/>)
This nice image of pc componentsis [produced](https://www.glukhov.org/) by [AI model Flux 1 dev](https://www.glukhov.org/post/2024/09/flux-text-to-image/).
## SearXNG Key Features.
Key features of SearXNG include:
  1. Privacy-focused: SearXNG does not collect user information, track searches, or create user profiles.
  2. Customizable: Users can personalize search settings, themes, and choose which search engines to use.
  3. Self-hosted option: It can be installed on a local network or personal computer for complete control over the search engine and associated data.
  4. Open-source: The platform invites collaboration and community-driven development.
  5. Ad-free experience: SearXNG does not serve advertisements or tracking content.
  6. Tor compatibility: Search queries can be routed through the Tor network for enhanced anonymity.


SearXNG offers categorical searching, allowing users to separate results into standard categories like “Web,” “Images,” “Videos,” and “News,” as well as non-standard categories such as “Social Media,” “Music,” “Files,” “IT,” and “Science”.
The metasearch engine removes private data from requests sent to search services and result pages, ensuring user privacy. It can be accessed through public or private instances, with a list of public instances available at searx.space.
## Selfhosting SearXNG
SearXNG is a free and open-source metasearch engine that can be installed on your own server or personal computer. Self-hosting SearXNG offers several benefits:
  1. Privacy control: You have full control over your search data and can ensure it’s not being collected or shared.
  2. Customization: You can personalize settings, themes, and choose which search engines to use.
  3. Ad-free experience: SearXNG doesn’t serve advertisements or tracking content.


However, there are some considerations when self-hosting SearXNG:
  1. Privacy trade-off: If you’re the only user of your self-hosted instance, your searches may be more easily identifiable by the underlying search engines.
  2. Technical knowledge: Setting up and maintaining a self-hosted instance requires some technical skills.
  3. Resource requirements: You’ll need a server or computer to run the SearXNG instance.


To self-host SearXNG, you can use Docker for easy installation and management. The process typically involves:
  1. Setting up a server or container environment
  2. Cloning the SearXNG Docker repository
  3. Configuring the application
  4. Running the Docker container


While self-hosting offers control and customization, it’s important to weigh the privacy implications and technical requirements before deciding to self-host SearXNG.
## SearXNG techincal requirements for self-hosting
SearXNG can be hosted on a variety of hardware configurations, from small single-board computers to more powerful servers. The hardware requirements for hosting SearXNG are relatively modest:
  1. Processor: A 64-bit system is recommended. Even a single core can be sufficient for small-scale usage.
  2. RAM: Minimum 512MB, with 2GB or more recommended for better performance.
  3. Storage: The Docker container takes up about 300MB of space. Additional storage may be needed depending on usage and logging requirements.
  4. Network: A stable internet connection is necessary, but bandwidth requirements depend on the number of users.


[Content truncated...]