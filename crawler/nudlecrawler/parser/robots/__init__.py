from typing import Set
from nudlecrawler.parser.robots.models import DomainRules

class RobotsParser:
    def __init__(self, domain: str):
        self.domain = domain
        self.rules: DomainRules = DomainRules()