"""Where to learn a skill fast, in Hindi (YouTube).

Only channels checked on 2026-10-07 (web search confirmed the channel teaches in Hindi and covers the topic).
Links are YouTube SEARCHES ("<skill> <channel>"), so they keep working even if a channel renames a playlist.
Skills without a verified channel get a general "<skill> tutorial in Hindi" search.
"""
from urllib.parse import quote_plus

CHANNELS = {  # channel -> what it is known for (shown as a hint)
    "CodeWithHarry": "Python, Django, web basics",
    "CampusX": "FastAPI, Python for ML",
    "GeekyShows": "Django and Django REST Framework",
    "Chai aur Code": "JavaScript, React, Node.js backend, Docker (Hitesh Choudhary)",
    "Apna College": "DSA, SQL (MySQL), Git & GitHub",
    "Gate Smashers": "DBMS and SQL concepts",
    "TrainWithShubham": "DevOps projects: Docker, Kubernetes, CI/CD, AWS",
    "CloudFolks HUB Hindi": "AWS, Docker, Kubernetes, Linux, Git, Terraform, Azure",
    "DevOps Molvi Hindi": "Docker, Kubernetes, Git, Linux (Hindi/Urdu)",
}

SKILL_CHANNELS = {
    "Python": ["CodeWithHarry"], "Django": ["CodeWithHarry", "GeekyShows"], "FastAPI": ["CampusX"],
    "REST APIs": ["GeekyShows", "Chai aur Code"],
    "JavaScript": ["Chai aur Code"], "TypeScript": ["Chai aur Code"], "React": ["Chai aur Code"],
    "Node.js": ["Chai aur Code"], "Express.js": ["Chai aur Code"],
    "SQL": ["Apna College", "Gate Smashers"], "PostgreSQL": ["Apna College", "Gate Smashers"], "MySQL": ["Apna College", "Gate Smashers"],
    "Git": ["Apna College", "CloudFolks HUB Hindi"],
    "Docker": ["TrainWithShubham", "CloudFolks HUB Hindi", "Chai aur Code"],
    "Kubernetes": ["TrainWithShubham", "CloudFolks HUB Hindi", "DevOps Molvi Hindi"],
    "AWS": ["CloudFolks HUB Hindi", "TrainWithShubham"], "Azure": ["CloudFolks HUB Hindi"],
    "Terraform": ["CloudFolks HUB Hindi", "TrainWithShubham"], "CI/CD": ["TrainWithShubham"],
    "Linux": ["CloudFolks HUB Hindi", "DevOps Molvi Hindi"],
    "DSA": ["Apna College"],
}


def _search(text: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(text)


def hindi_videos(skill: str) -> list[dict]:
    """[{channel, about, url}] for a skill: verified Hindi channels first, then a general Hindi search."""
    topic = skill.split(" (")[0]
    links = [{"channel": c, "about": CHANNELS[c], "url": _search(f"{topic} {c}")} for c in SKILL_CHANNELS.get(topic, [])]
    links.append({"channel": "YouTube search", "about": f"“{topic} tutorial in Hindi”", "url": _search(f"{topic} tutorial in Hindi")})
    return links
