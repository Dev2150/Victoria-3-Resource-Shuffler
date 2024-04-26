import functools
import os
import re
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from Auxiliary import copyTree

class RenameDialog(ctk.CTkToplevel):
    """Handles the input and the validation of the new name for the new version"""
    def __init__(self, name, app, pathAppdataVersions, pathGameStateRegions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("400x300")
        self.grab_set()

        self.label = ctk.CTkLabel(self, text="New name:")
        self.label.grid(row=0, column=0, padx=(10, 5), pady=10)

        self.entry = ctk.CTkEntry(self, width = 300)
        self.entry.insert(0, name)
        self.entry.grid(row=1, column=0, padx=(10, 5), pady=10)
        

        self.btnRename = ctk.CTkButton(self, text = "Confirm",
                                 command=functools.partial(renameCallback, self, app, pathAppdataVersions, pathGameStateRegions))
        self.btnRename.grid(row=2, column=0, padx=(10, 5), pady=10)

def renameCallback(self, app, pathAppdataVersions, pathGameStateRegions):
    """On button press, perform validation of the new version name"""
    def callback():
        newName = self.entry.get()
        versions = app.comboBoxVersions.cget('values')
        invalidCharacters = '^\\/:*?"<>|'
        if newName == "original":
            CTkMessagebox(title="Error", message='Will not overwrite "original" version', icon="cancel")
            return        
        for version in versions:
            if newName == version:
                CTkMessagebox(title="Error", message='Version name already exists', icon="cancel")
                return
        if not re.match(r'^[' + invalidCharacters + r']*$', newName):
            CTkMessagebox(title="Error", message=f'Version name cannot contain {invalidCharacters}', icon="cancel") 
        else:
            versions.append(newName)
            app.comboBoxVersions.configure(values=versions)
            app.comboBoxVersions.set(newName)
             
            pathVersion = os.path.join(pathAppdataVersions, newName)
            pathVersionConfigFile = os.path.join(pathVersion, 'config.ini')
            pathVersionStateRegions = os.path.join(pathVersion, 'state_regions')
            os.makedirs(pathVersionStateRegions)
            
            with open(pathVersionConfigFile, "w+") as f:
                for resKey, resource in app.resources.items():
                    if resource['isShuffled']:
                        f.write(resKey + " ")
            
            if not os.path.exists(pathVersionStateRegions):
                CTkMessagebox(title="Error", message=f'Cannot find {pathVersionStateRegions}', icon="cancel")
            else:
                copyTree(pathGameStateRegions, pathVersionStateRegions)
                self.destroy()
                CTkMessagebox(title="Success", message=f"You are now ready to play with the new version '{newName}'!", icon="check", option_1="OK")
    callback()
    return callback