from setuptools import (
    setup,
    find_packages,
)


with open('README.md') as fh:
    long_description = fh.read()

with open('requirements.txt') as rf:
    requires = rf.read().splitlines()

setup(
    name='P2Pslyr',
    version='0.1',
    description='P2P slayer',
    long_description=long_description,
    install_requires=requires,
    packages=find_packages(),
)
