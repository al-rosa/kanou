# setup.py
from setuptools import find_packages, setup

setup(
    name="fragrantica_scraper",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "playwright>=1.40.0",
        "fake-useragent>=1.4.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.2"
    ],
    python_requires=">=3.9",
)
