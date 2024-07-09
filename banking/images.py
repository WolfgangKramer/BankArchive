"""
    Images stored as PhotoImage objects, for buttons and logos.
    Created Oct 2008
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
from tkinter import PhotoImage


def currency_sign():
    '''
    Button activate/deactivate Toolbar
    Switch off/on currency_sign in columns of type decimal
    '''
    img = PhotoImage(format='gif', data=(
        'iVBORw0KGgoAAAANSUhEUgAAACAAAAAXCAIAAADlZ9q2AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8'
        + 'YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAB8SURBVEhL7dTBCcAgDAXQ2EG8OIwrePTsJoorOosN7b8n'
        + 'EYRCfReNoB8h6uactNOFcZsTIDoBIltAKcU9WmtYkhgeGh/qvU8poVbiAI1aKzYQhRCwqqANYDFGzCw+'
        + 'doMxBgo1QxflnHvvKNQMAW//bGzTNX/7KhacAAHRDUMsdGzYDmA9AAAAAElFTkSuQmCC')
    )
    return img
