'''
Created on 02.01.2026
__updated__ = "2026-05-26"
@author: Wolfgang Kramer
'''

from dataclasses import dataclass


@dataclass
class ConnectionResult:
    user: str = 'root'
    password: str = 'FINTS'
    host: str = 'localhost'
    database: str = ''
    connected: bool = False
    conn = None
    cursor = None
    engine = None


connectionresult = ConnectionResult()
