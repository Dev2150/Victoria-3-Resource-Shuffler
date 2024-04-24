import os
import re
import shutil
from Auxiliary import copyTree
from globalProperties import resourcesToIgnore
from CTkMessagebox import CTkMessagebox

def switch_resource_callback(resKey, resources, comboBoxPresets, logger):
    def callback():
        value = resources[resKey]['stringVar'].get()
        if value == "1":
            resources[resKey]['isShuffled'] = True
        else:
            resources[resKey]['isShuffled'] = False
        comboBoxPresets.set('Custom')
        logger.info(f'{resKey}: {resources[resKey]['isShuffled']}')
    return callback

def switch_resource_preset_callback(value, resources):
    def callback():
        for resourceName, resource in resources.items():
            if resourceName in resourcesToIgnore:
                continue
            resource['isShuffled'] = False
            resource['stringVar'].set("0")

            if  value == "All" or \
                resourceName == 'gold' and value != "Vanilla - No shuffle" or \
                resourceName == 'oil' and value not in ["Vanilla - No shuffle", "Gold"] or \
                resourceName in ['coal', 'iron', 'lead', 'sulfur'] and value not in ["Vanilla - No shuffle", "Gold", "Yellow & Black Gold", "Discoverables"] or \
                resourceName == 'rubber' and value in ["All but wood", "All", "Discoverables"]:

                resource['isShuffled'] = True
                resource['stringVar'].set("1")
    callback()            
    return callback

def submit_rename(self, app, pathAppdataVersions, pathGameStateRegions):
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
            CTkMessagebox(title="Error", message=f'Variant name cannot contain {invalidCharacters}', icon="cancel") 
        else:
            versions.append(newName)
            app.comboBoxVersions.configure(values=versions)
            app.comboBoxVersions.set(newName)
             
            pathVersion = os.path.join(pathAppdataVersions, newName, 'state_regions')
            os.makedirs(pathVersion)
            copyTree(pathGameStateRegions, pathVersion)
            self.destroy()
            CTkMessagebox(message=f"You are now ready to play with the new variant '{newName}'!", icon="check", option_1="OK")
    callback()
    return callback