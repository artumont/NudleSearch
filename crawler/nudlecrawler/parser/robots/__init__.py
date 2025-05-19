from typing import Dict, List, Optional
from .models import RobotRules


class RobotsParser:
    """A parser for robots.txt files that extracts crawling rules for different user agents.

    This class parses robots.txt files and maintains a mapping of user agents to their
    respective crawling rules, including allowed/disallowed paths and sitemaps.

    Attributes:
        _rules_map (Dict[str, RobotRules]): Mapping of user agents to their RobotRules
        _current_agents (List[str]): List of user agents currently being processed

    Example:
        >>> parser = RobotsParser()
        >>> rules = parser.parse("User-agent: *\\nDisallow: /private/")
        >>> specific_rules = parser.get_rules("nudle-bot")
    """

    def __init__(self):
        self._rules_map: Dict[str, RobotRules] = {}
        self._current_agents: List[str] = []

    # @context: Public
    def parse(self, content: str) -> Dict[str, RobotRules]:
        """Parse robots.txt content and return rules for all user agents.

        Args:
            content (str): The content of the robots.txt file

        Returns:
            Dict[str, RobotRules]: Mapping of user agents to their respective rules

        Example:
            >>> parser = RobotsParser()
            >>> rules = parser.parse("User-agent: *\\nDisallow: /private/")
        """
        self._rules_map.clear()
        self._current_agents.clear()

        self._rules_map["*"] = RobotRules("*")

        for line in content.split('\n'):
            self._parse_line(line.strip())

        return self._rules_map

    def get_rules(self, user_agent: str = "nudle-bot") -> RobotRules:
        """Get the rules that apply to a specific user agent.

        Args:
            user_agent (str): The user agent to get rules for

        Returns:
            RobotRules: Rules that apply to the specified user agent
        """
        if user_agent in self._rules_map:
            return self._rules_map[user_agent]

        # @note: Fallback to default rules
        return self._rules_map.get("*", RobotRules(user_agent))

    # @context: Private
    def _parse_line(self, line: str) -> None:
        """Parse a single line from robots.txt.

        Args:
            line (str): A line from robots.txt file
        """
        if not line or line.startswith('#'):
            return

        parts = line.split(':', 1)
        if len(parts) != 2:
            return

        field = parts[0].strip().lower()
        value = parts[1].strip()

        if field == "user-agent":
            self._handle_user_agent(value)
        elif field == "disallow":
            self._handle_disallow(value)
        elif field == "allow":
            self._handle_allow(value)
        elif field == "sitemap":
            self._handle_sitemap(value)

    def _handle_user_agent(self, agent: str) -> None:
        """Handle a User-agent line in robots.txt.

        Args:
            agent (str): User agent string

        Note:
            This method supports consecutive User-agent directives by maintaining
            a list of current agents. Each User-agent directive adds to this list
            until a non-User-agent directive is encountered.
        """
        agent = agent.lower()
        if agent not in self._rules_map:
            self._rules_map[agent] = RobotRules(agent)

        # @note: If last line wasn't User-agent, clear the current agents list
        if not (hasattr(self, '_last_directive') and self._last_directive == "user-agent"):
            self._current_agents = []

        self._current_agents.append(agent)
        self._last_directive = "user-agent"

    def _handle_disallow(self, path: str) -> None:
        self._last_directive = "disallow"
        """Handle a Disallow line in robots.txt.

        Args:
            path (str): Path to disallow
        """
        if not self._current_agents:
            self._current_agents = ["*"]

        for agent in self._current_agents:
            try:
                self._rules_map[agent].add_disallowed_path(path)
            except ValueError:
                continue

    def _handle_allow(self, path: str) -> None:
        self._last_directive = "allow"
        """Handle an Allow line in robots.txt.

        Args:
            path (str): Path to allow
        """
        if not self._current_agents:
            self._current_agents = ["*"]

        for agent in self._current_agents:
            try:
                self._rules_map[agent].add_allowed_path(path)
            except ValueError:
                continue

    def _handle_sitemap(self, url: str) -> None:
        self._last_directive = "sitemap"
        """Handle a Sitemap line in robots.txt.

        Args:
            url (str): URL of the sitemap
        """
        for rules in self._rules_map.values():
            try:
                rules.add_sitemap(url)
            except ValueError:
                continue
