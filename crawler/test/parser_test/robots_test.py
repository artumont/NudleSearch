import pytest
from nudlecrawler.parser.robots import RobotsParser
from nudlecrawler.parser.robots.models import RobotRules

def test_basic_parsing():
    """Test basic robots.txt parsing functionality."""
    parser = RobotsParser()
    content = """
    User-agent: *
    Disallow: /private/
    Allow: /public/
    Sitemap: https://example.com/sitemap.xml
    """
    rules = parser.parse(content)
    
    assert "*" in rules
    assert rules["*"].disallowed_paths == ["/private/"]
    assert rules["*"].allowed_paths == ["/public/"]
    assert rules["*"].sitemaps == ["https://example.com/sitemap.xml"]

def test_multiple_user_agents():
    """Test handling of multiple User-agent sections."""
    parser = RobotsParser()
    content = """
    User-agent: bot1
    Disallow: /bot1-private/

    User-agent: bot2
    Disallow: /bot2-private/
    Allow: /bot2-public/
    """
    rules = parser.parse(content)
    
    assert "bot1" in rules
    assert "bot2" in rules
    assert rules["bot1"].disallowed_paths == ["/bot1-private/"]
    assert rules["bot2"].disallowed_paths == ["/bot2-private/"]
    assert rules["bot2"].allowed_paths == ["/bot2-public/"]

def test_specific_bot_rules():
    """Test getting rules for a specific user agent."""
    parser = RobotsParser()
    content = """
    User-agent: nudle-bot
    Disallow: /private/
    Allow: /public/

    User-agent: *
    Disallow: /all-private/
    """
    parser.parse(content)
    
    nudle_rules = parser.get_rules("nudle-bot")
    assert nudle_rules.disallowed_paths == ["/private/"]
    assert nudle_rules.allowed_paths == ["/public/"]
    
    other_rules = parser.get_rules("other-bot")
    assert other_rules.disallowed_paths == ["/all-private/"]

def test_empty_content():
    """Test parsing empty robots.txt content."""
    parser = RobotsParser()
    rules = parser.parse("")
    
    assert "*" in rules
    assert not rules["*"].disallowed_paths
    assert not rules["*"].allowed_paths
    assert not rules["*"].sitemaps

def test_invalid_lines():
    """Test handling of invalid lines in robots.txt."""
    parser = RobotsParser()
    content = """
    Invalid line
    Not: valid
    User-agent: *
    Disallow: /private/
    Random text
    """
    rules = parser.parse(content)
    
    assert "*" in rules
    assert rules["*"].disallowed_paths == ["/private/"]

def test_multiple_sitemaps():
    """Test handling of multiple Sitemap directives."""
    parser = RobotsParser()
    content = """
    User-agent: *
    Sitemap: https://example.com/sitemap1.xml
    Sitemap: https://example.com/sitemap2.xml
    """
    rules = parser.parse(content)
    
    assert rules["*"].sitemaps == [
        "https://example.com/sitemap1.xml",
        "https://example.com/sitemap2.xml"
    ]

def test_path_validation():
    """Test validation of paths in Allow/Disallow directives."""
    parser = RobotsParser()
    content = """
    User-agent: *
    Disallow: 
    Disallow: /valid/path
    Allow: 
    Allow: /another/valid/path
    """
    rules = parser.parse(content)
    
    assert rules["*"].disallowed_paths == ["/valid/path"]
    assert rules["*"].allowed_paths == ["/another/valid/path"]

def test_is_allowed_checking():
    """Test the is_allowed path checking functionality."""
    parser = RobotsParser()
    content = """
    User-agent: *
    Disallow: /private/
    Allow: /private/public/
    """
    rules = parser.parse(content)
    bot_rules = rules["*"]
    
    assert not bot_rules.is_allowed("/private/secret")
    assert bot_rules.is_allowed("/private/public/page")
    assert bot_rules.is_allowed("/public/page")

def test_case_insensitive_user_agent():
    """Test case-insensitive handling of User-agent values."""
    parser = RobotsParser()
    content = """
    User-agent: Bot-Name
    Disallow: /private/
    """
    rules = parser.parse(content)
    
    assert "bot-name" in rules
    bot_rules = parser.get_rules("BOT-NAME")
    assert bot_rules.disallowed_paths == ["/private/"]

def test_consecutive_user_agents():
    """Test handling of consecutive User-agent directives."""
    parser = RobotsParser()
    content = """
    User-agent: bot1
    User-agent: bot2
    Disallow: /private/
    """
    rules = parser.parse(content)
    
    assert rules["bot1"].disallowed_paths == ["/private/"]
    assert rules["bot2"].disallowed_paths == ["/private/"]
