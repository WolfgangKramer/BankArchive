'''
Created on 12.12.2023

@author: Wolfg
'''

from setuptools import setup

setup(
    name='banking',
    description='Bank Archive',
    author='Wolfgang Kramer',
    author_email='simbolury@gmail.com',
    packages=['banking'],
    install_requires=['fints',
                      'mariadb'
                      'pandastable'
                      'selenium'
                      'simplejson'
                      'yfinance'
                      'sqlalchemy'
                      ],
)
