from setuptools import (
    setup,
    find_packages,
)


with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", encoding="utf-8") as rf:
    requires = rf.read().splitlines()

setup(
    name="P2Pslyr",
    version="0.1",
    description="P2P slayer",
    long_description=long_description,
    install_requires=requires,
    packages=find_packages(),
)
