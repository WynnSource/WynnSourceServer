import tomllib

with open("pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

__NAME__ = "WynnSource Server"
__VERSION__: str = pyproject["project"]["version"]
__DESCRIPTION__: str = pyproject["project"]["description"]
__REVISION__ = 1
