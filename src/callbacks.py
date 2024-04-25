from datetime import datetime
import os
from Auxiliary import copyTree
from DialogRename import RenameDialog
from globalProperties import IGNORED_RESOURCES, TEXT_DEFAULT_BEST_STATES
from CTkMessagebox import CTkMessagebox
import subprocess

from readFromGameFiles import getInfoFromStateRegions, getResourcesFromCompanies, getResourcesFromHistory
from services import clearCollectedResources, findStatesWithMostResources, getStatesInfo, loadVersionConfigFile, makeBackUp, restoreStateRegions, shuffleResources, trimStateRegions

def execute(app, versions, pathAppdataVersions, pathGameStateRegions, pathAppdataStateRegionsOriginal, pathGameHistoryBuildings, pathGameCompanies, logger):
    def callback():
        if app.top is None or not app.top.winfo_exists():

            makeBackUp(pathGameStateRegions, pathAppdataStateRegionsOriginal, logger)
            stateCount, stateInfo, stateNameToID, stateIDToName = getStatesInfo(pathGameStateRegions, logger)
            clearCollectedResources(stateCount, app.resources)
            app.resources, stateInfo = getInfoFromStateRegions(pathGameStateRegions, stateInfo, app.resources, logger)
            app.resources = getResourcesFromHistory(pathGameHistoryBuildings, app.resources, logger)
            app.resources = getResourcesFromCompanies(stateNameToID, stateIDToName, app.resources, pathGameCompanies, logger)
            trimStateRegions(pathGameStateRegions, logger)
            app.resources = shuffleResources(app.resources, logger, stateIDToName)
            restoreStateRegions(pathGameStateRegions, stateInfo, app.resources, logger)
            app.resources = findStatesWithMostResources(app.resources, stateCount)
            switchBestStatesCallback(app, stateIDToName, logger)

            now = datetime.now()
            name = app.comboBoxPresets.get() + " " + f" {now.year}-{now.month:02d}-{now.day:02d}  {now.hour:02d}-{now.minute:02d}-{now.second:02d}"

            app.top = RenameDialog(name, app, pathAppdataVersions, pathGameStateRegions)  # create window if its None or destroyed

        app.top.focus()  # if window exists focus it
    return callback

def switchResourceCallback(resKey, resources, comboBoxPresets, logger):
    def callback():
        value = resources[resKey]['stringVar'].get()
        if value == "1":
            resources[resKey]['isShuffled'] = True
        else:
            resources[resKey]['isShuffled'] = False
        comboBoxPresets.set('Custom')
        logger.info(f'{resKey}: {resources[resKey]['isShuffled']}')
    return callback

def switchResourcePresetCallback(value, resources):
    def callback():
        for resourceName, resource in resources.items():
            if resourceName in IGNORED_RESOURCES:
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

def openFolderCallback(app, pathAppdataVersions):
    def callback():
        currentVersion = app.comboBoxVersions.get()
        currentPath = os.path.join(pathAppdataVersions, currentVersion)
        subprocess.Popen(r'explorer /select,' + currentPath + "\\")
    return callback

def switchVersionCallback(app, pathAppdataVersions, pathGameStateRegions, logger, nothing):
    def callback():
        currentVersion = app.comboBoxVersions.get()
        currentVersionPath = os.path.join(pathAppdataVersions, currentVersion, 'state_regions')
        if not os.path.exists(currentVersionPath):
            CTkMessagebox(title="Error", message="The version's folder does not exist", icon="cancel")
        else:
            # for file in  os.listdir(pathGameStateRegions):
            #     filePath = os.path.join(pathGameStateRegions, file)
            #     os.remove(filePath)
            copyTree(currentVersionPath, pathGameStateRegions)
            logger.info(f"Copied from {currentVersionPath} to {pathGameStateRegions}")
            CTkMessagebox(title="Success", message=f"You are now ready to play with the version '{currentVersion}'!", icon="check", option_1="OK")

            stateCount, stateInfo, stateNameToID, stateIDToName = getStatesInfo(pathGameStateRegions, logger)
            clearCollectedResources(stateCount, app.resources)
            app.resources, stateInfo = getInfoFromStateRegions(pathGameStateRegions, stateInfo, app.resources, logger)
            app.resources = findStatesWithMostResources(app.resources, stateCount)
            switchBestStatesCallback(app, stateIDToName, logger)
            loadVersionConfigFile(app, pathAppdataVersions)

    callback()
    return callback

def switchBestStatesCallback(app, stateIDToName, logger):
    def callback():
        if app.switchMaxResources.get() == "0":
            for resName, resource in app.resources.items():
                if resName in IGNORED_RESOURCES:
                    continue
                resource['labelBestStates'].set(TEXT_DEFAULT_BEST_STATES)        
        else:
            for resName, resource in app.resources.items():
                if resName in IGNORED_RESOURCES:
                    continue
                text = ""
                for bestState in resource['bestStates']:
                    state = stateIDToName[bestState][6:].capitalize()
                    text +=  state + " "
                resource['labelBestStates'].set(text)

    callback()
    return callback