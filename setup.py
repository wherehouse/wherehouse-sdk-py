from codecs import open as codecs_open

from setuptools import setup, find_packages


# Get the long description from the README file
with codecs_open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

# Parse the version from the wherehouse module.
with open('wherehouse/__init__.py') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

setup(name='wherehouse',
      version=version,
      description="A Python client for Wherehouse modules",
      long_description=long_description,
      classifiers=[],
      keywords='',
      author="Dan Abdinoor",
      author_email='dan@wherehou.se',
      url='https://github.com/wherehouse/wherehouse-sdk-py',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=['pyshp>=1.2.10'],
      extras_require={'test': ['pytest>=2.8.3']})
