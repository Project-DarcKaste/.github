'''Debug Options Menu
---
<hr/>

This is the devtools menu for DarcKaste

Most of this is probably experimental, and I kinda suck at python as of 11/7/2025, so expect bugs...
<hr/>

<code>Coded by: Jayden Mays</code>
'''
import tkinter as tk
import pygame
import json
import os
import cryptography
from cryptography.fernet import Fernet as fern

class DevTools:
    '''## Devtools for Project DarcKaste'''
    def set_password(password: bytes= b"123456"):
        '''Sets and encrypts the password'''
        key = fern.generate_key()
        PSWD = fern.encrypt(self=fern(key), data=password)
        print(PSWD, "\n", fern.decrypt(fern(key), PSWD))
    
    def dt_window(title="Devtools",icon="Assets\\Icons\\devtools.ico",wid=300,hei=450,x=10,y=10,text="placeholder"):
        '''DevTools Window using Tkinter'''
        debug = tk.Tk()
        debug.title(title)
        debug.iconbitmap(bitmap=icon)

        debug.geometry(f"{wid}x{hei}+{x}+{y}")
        frame = tk.Frame(debug,relief="flat")
        label = tk.Label(frame,text=text)


        debug.mainloop()

    

