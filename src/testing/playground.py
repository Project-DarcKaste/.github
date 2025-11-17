'''Playground
---
This is the place where functions get bug tested...
<hr/>
<code>Coded by: Jayden Mays</code>
'''
import sys, os

sys.path.append("src")

import debug_menu
from debug_menu import DevTools 

#test devtools
DevTools.set_password(b"test-password")
DevTools.dt_window(icon="Assets\\_Debug\\test_favicon.bmp")
