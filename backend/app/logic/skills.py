"""The list of skills we can recognise in job descriptions and CVs.

To add a skill: add one line to SKILLS -> "Name": [regex patterns].
Patterns are matched case-insensitively as whole words.
"""
import re
from functools import cache

SKILLS: dict[str, list[str]] = {
    # languages
    "Python": [r"python"],
    "JavaScript": [r"javascript", r"es6"],
    "TypeScript": [r"typescript"],
    "Java": [r"java(?!\s*script)"],
    "C#": [r"c#"],
    "C++": [r"c\+\+"],
    "Go": [r"golang"],
    "SQL": [r"sql"],
    # backend
    "FastAPI": [r"fast\s*api"],
    "Django": [r"django"],
    "Flask": [r"flask"],
    "Node.js": [r"node\.?js"],
    "Express.js": [r"express\.?js"],
    ".NET": [r"\.net", r"asp\.net"],
    "REST APIs": [r"rest(?:ful)?\s*apis?", r"restful"],
    "GraphQL": [r"graphql"],
    "Microservices": [r"micro-?services?"],
    "JWT": [r"jwt"],
    "OAuth": [r"oauth\s*2?(?:\.0)?"],
    "RBAC": [r"rbac", r"role[- ]based access"],
    # frontend
    "React": [r"react(?:\.?js)?"],
    "Angular": [r"angular(?:js)?"],
    "Vue.js": [r"vue(?:\.?js)?"],
    "HTML": [r"html5?"],
    "CSS": [r"css3?", r"scss"],
    # databases / messaging
    "PostgreSQL": [r"postgres(?:ql)?"],
    "MySQL": [r"mysql", r"mariadb"],
    "MongoDB": [r"mongo(?:db)?"],
    "Redis": [r"redis"],
    "InfluxDB": [r"influx\s*db"],
    "Kafka": [r"kafka"],
    "RabbitMQ": [r"rabbit\s*mq"],
    "MQTT": [r"mqtt"],
    # devops / cloud
    "Docker": [r"docker", r"containers?"],
    "Kubernetes": [r"kubernetes", r"k8s"],
    "AWS": [r"aws", r"amazon web services", r"ec2"],
    "Azure": [r"azure"],
    "GCP": [r"gcp", r"google cloud"],
    "Terraform": [r"terraform"],
    "CI/CD": [r"ci\s*/\s*cd"],
    "Linux": [r"linux"],
    "Git": [r"git", r"github", r"gitlab"],
    # industrial / OT
    "SCADA": [r"scada"],
    "WebSCADA": [r"web\s*-?scada"],
    "OPC UA": [r"opc[\s-]?ua"],
    "OPC": [r"opc(?![\s-]?ua)"],
    "Modbus": [r"modbus"],
    "FINS": [r"fins"],
    "PLC": [r"plcs?", r"sps"],
    "MES": [r"mes", r"manufacturing execution systems?"],
    "IIoT": [r"iiot", r"industrial iot", r"iot"],
    "HMI": [r"hmi"],
    "Siemens S7 / TIA": [r"tia portal", r"simatic", r"s7-?\d{3,4}"],
    "PROFINET": [r"profinet"],
    "Industrial Automation": [r"industrial automation", r"factory automation"],
    "Industry 4.0": [r"industr(?:y|ie) 4\.0"],
    "Node-RED": [r"node-?red"],
    "LabVIEW": [r"labview"],
    "Zenon": [r"zenon"],
    "21 CFR Part 11": [r"21\s*cfr\s*(?:part\s*)?11", r"gxp", r"gmp"],
    "PyInstaller": [r"pyinstaller"],
    "Windows Services": [r"windows services?", r"nssm"],
    # testing / other
    "Unit Testing": [r"unit[- ]test(?:s|ing)?", r"pytest", r"jest"],
    "Agile": [r"agile", r"scrum"],
    "Postman": [r"postman"],
    "Machine Learning": [r"machine learning"],
}

# Similar skills get HALF credit (e.g. you know MySQL, the job wants PostgreSQL).
RELATED = [
    {"PostgreSQL", "MySQL", "SQL"},
    {"React", "Angular", "Vue.js"},
    {"FastAPI", "Django", "Flask"},
    {"Node.js", "Express.js"},
    {"AWS", "Azure", "GCP"},
    {"OPC UA", "OPC", "Modbus", "FINS", "PROFINET", "MQTT"},
    {"SCADA", "WebSCADA", "HMI"},
    {"JavaScript", "TypeScript"},
    {"JWT", "OAuth", "RBAC"},
    {"Kafka", "RabbitMQ", "MQTT"},
]

# If you have the first skill, you also have the second.
IMPLIES = {"WebSCADA": ["SCADA"], "OPC UA": ["OPC"], "Express.js": ["Node.js"], "MySQL": ["SQL"], "PostgreSQL": ["SQL"],
           # writing TypeScript / Node.js / React means writing JavaScript; Angular apps are written in TypeScript
           "TypeScript": ["JavaScript"], "Node.js": ["JavaScript"], "React": ["JavaScript"], "Angular": ["TypeScript"]}


@cache
def _patterns() -> dict[str, re.Pattern]:
    return {
        name: re.compile(r"(?<![\w.#+-])(?:" + "|".join(pats) + r")(?![\w#+])", re.IGNORECASE)
        for name, pats in SKILLS.items()
    }


def find_skills(text: str) -> dict[str, int]:
    """Return {skill: number of mentions} found in the text."""
    found = {}
    for name, pattern in _patterns().items():
        count = len(pattern.findall(text))
        if count:
            found[name] = count
    return found


def canonical_skill(name: str) -> str:
    """'nodejs' -> 'Node.js', 'AWS EC2' -> 'AWS'. Unknown names are kept as typed."""
    for skill in SKILLS:
        if skill.lower() == name.strip().lower():
            return skill
    found = find_skills(name)
    return max(found, key=found.get) if found else name.strip()


def with_implied(skills: set[str]) -> set[str]:
    """Skills plus everything they imply, following chains (Express.js → Node.js → JavaScript)."""
    result, todo = set(skills), list(skills)
    while todo:
        for implied in IMPLIES.get(todo.pop(), []):
            if implied not in result:
                result.add(implied)
                todo.append(implied)
    return result


def related_skill(wanted: str, have: set[str]) -> str | None:
    for group in RELATED:
        if wanted in group:
            for h in sorted(have):
                if h in group and h != wanted:
                    return h
    return None
