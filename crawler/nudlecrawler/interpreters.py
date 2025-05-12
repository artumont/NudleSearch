import re
from typing import List
from .connection import ConnectionManager


class RobotsTXT:
    def __init__(self, contents: str):
        self.content = contents
        self.whitelist = self._get_blacklist()
        self.blacklist = self._get_whitelist()

    def _get_blacklist(self) -> List[str]:
        pass

    def _get_whitelist(self) -> List[str]:
        pass
