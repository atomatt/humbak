from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='humbak',
      version=version,
      description="Simple backup tool for humyo.com, using the DAV API",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Matt Goodall',
      author_email='matt.goodall@gmail.com',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      [console_scripts]
      humbak = humbak.main:main
      """,
      )
