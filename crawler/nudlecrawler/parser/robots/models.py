from typing import List


class RobotRules:
    """A class that represents and manages robots.txt rules for web crawling.
    
    This class handles the rules defined in a robots.txt file, including allowed and
    disallowed paths for specific user agents, as well as sitemap locations.
    
    Attributes:
        user_agent (str): The user agent string for the crawler (default: "nudle-bot")
        disallowed_paths (List[str]): List of URL paths that are disallowed by robots.txt
        allowed_paths (List[str]): List of URL paths that are explicitly allowed by robots.txt
        sitemaps (List[str]): List of sitemap URLs specified in robots.txt
        
    Example:
        >>> rules = RobotRules("my-crawler")
        >>> rules.allowed_paths.append("/blog")
        >>> rules.disallowed_paths.append("/private")
        >>> rules.is_allowed("/blog/post1")
    """

    def __init__(self, user_agent: str = "nudle-bot"):
        """Initialize RobotsTxt parser.

        Args:
            user_agent (str, optional): User agent string to identify the bot. Defaults to "nudle-bot".

        Attributes:
            user_agent (str): User agent string for the bot
            disallowed_paths (List[str]): List of paths disallowed by robots.txt
            allowed_paths (List[str]): List of paths explicitly allowed by robots.txt
            sitemaps (List[str]): List of sitemap URLs specified in robots.txt
        """
        self.user_agent: str = user_agent
        self.disallowed_paths: List[str] = []
        self.allowed_paths: List[str] = []
        self.sitemaps: List[str] = []

    def is_allowed(self, path: str) -> bool:
        """Determines if a given path is allowed according to the robots.txt rules.

        The method checks the path against both allowed and disallowed paths defined in robots.txt.
        First checks if path matches any allowed paths, then checks against disallowed paths.

        Args:
            path (str): The URL path to check for permission

        Returns:
            bool: True if the path is allowed, False if it is disallowed

        Examples:
            >>> robot = RobotsParser()
            >>> robot.is_allowed("/allowed/path")
            True
            >>> robot.is_allowed("/disallowed/path") 
            False
        """
        if any(path.startswith(allowed_path) for allowed_path in self.allowed_paths):
            return True

        if any(path.startswith(disallowed_path) for disallowed_path in self.disallowed_paths):
            return False
        return True
    
    def add_disallowed_path(self, path: str) -> None:
        """Adds a disallowed path to the robots.txt rules.
        
        Args:
            path: The URL path to disallow
            
        Raises:
            ValueError: If path is empty or not a string
        """
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Path must be a non-empty string")
        self.disallowed_paths.append(path.strip())

    def add_allowed_path(self, path: str) -> None:
        """Adds an allowed path to the robots.txt rules.
        
        Args:
            path: The URL path to allow
            
        Raises:
            ValueError: If path is empty or not a string
        """
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Path must be a non-empty string")
        self.allowed_paths.append(path.strip())

    def add_sitemap(self, sitemap: str) -> None:
        """Adds a sitemap URL to the robots.txt rules.
        
        Args:
            sitemap: The sitemap URL to add
            
        Raises:
            ValueError: If sitemap URL is empty or not a string
        """
        if not isinstance(sitemap, str) or not sitemap.strip():
            raise ValueError("Sitemap URL must be a non-empty string")
        self.sitemaps.append(sitemap.strip())
