from typing import Dict


class DomainRules:
    """A class to represent and manage the rules defined in a robots.txt file for a specific website.

    This class handles parsing and storing directives from robots.txt files, including
    allow/disallow rules, crawl delays, and other site-specific crawler directives.

    Attributes:
        None defined yet.

    Example:
        ```
        site_rules = DomainRules()
        ```
    """
    
    def __init__(self):
        """Initialize a new instance of the robots.txt parser.

        Attributes:
            permission_list (Dict[str, bool]): Dictionary mapping URL patterns to boolean permission values.
            crawl_delay (int): Number of seconds to wait between successive requests.
            sitemaps (list[str]): List of sitemap URLs found in robots.txt.
        """
        self.permission_list: Dict[str, bool] = {}
        self.user_agent: str = "*"
        self.crawl_delay: int = 0
        self.sitemaps: list[str] = []
    
    def is_allowed(self, url: str) -> bool:
        """Check if a given URL is allowed to be crawled based on the rules.

        Args:
            url (str): The URL to check against the robots.txt rules.

        Returns:
            bool: True if the URL is allowed, False otherwise.
        """
        return self.permission_list.get(url, True)