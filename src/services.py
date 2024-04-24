import os
from random import shuffle
import re
import shutil
from typing import List
from globalProperties import logger, resourcesToIgnore
from Auxiliary import copyTree
from DialogRename import RenameDialog
from readFromGameFiles import getInfoFromStateRegions, getResourcesFromCompanies, getResourcesFromHistory
from datetime import date, datetime

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
            shuffleResources(app.resources, logger, stateIDToName)
            restoreStateRegions(pathGameStateRegions, stateInfo, app.resources, logger)
            
            now = datetime.now()
            name = app.comboBoxPresets.get() + " " + f" {now.year}-{now.month:02d}-{now.day:02d}--{now.hour:02d}-{now.minute:02d}-{now.second:02d}"

            app.top = RenameDialog(name, app, pathAppdataVersions, pathGameStateRegions)  # create window if its None or destroyed

        app.top.focus()  # if window exists focus it
    return callback

def makeBackUp(pathGameStateRegions, pathAppdataStateRegionsOriginal, logger):
    if not os.path.exists(pathAppdataStateRegionsOriginal):
        os.makedirs(pathAppdataStateRegionsOriginal)
        copyTree(pathGameStateRegions, pathAppdataStateRegionsOriginal)
        logger.info("Made a back-up from %appdata%")
    else:
        copyTree(pathAppdataStateRegionsOriginal, pathGameStateRegions)
        logger.info("Game's state_region replaced by the back-up from %appdata%")

def configureGamePath(pathGame, pathAppdataStateRegionsOriginal, logger):
    validPath = True

    pathGameStateRegions = os.path.join(pathGame, "game", "map_data", "state_regions")
    pathGameHistoryBuildings = os.path.join(pathGame, "game", "common", "history", "buildings")
    pathGameCompanies = os.path.join(pathGame, "game", "common", "company_types")
    pathGameGoodIcons = os.path.join(pathGame, "game", "gfx", "interface", "icons", "goods_icons")
    if not os.path.exists(pathGame):
        logger.error("Path to Victoria 3 folder does not exist in config file")
        validPath = False
    if not os.path.exists(pathGameStateRegions):
        logger.error(f"Path does not correspond to Victoria 3 folder; Expected {pathGameStateRegions}")
        validPath = False
    if not os.path.exists(pathGameHistoryBuildings):
        logger.error(f"Path does not correspond to Victoria 3 folder; Expected {pathGameHistoryBuildings}")
        validPath = False
    if not os.path.exists(pathGameCompanies):
        logger.error(f"Path does not correspond to Victoria 3 folder; Expected {pathGameCompanies}")
        validPath = False
    
    if not validPath: 
        return validPath, None, None, None, None, None

    makeBackUp(pathGameStateRegions, pathAppdataStateRegionsOriginal, logger)
    
    return validPath, pathGame, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, pathGameGoodIcons

def getStatesInfo(pathGameStateRegions, logger):
    stateCount = 0
    stateNameToID = {}
    stateIDToName = {}
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            with open(filePath, "r") as f:
                for line in f:
                    findState = re.search("(STATE_.*) =.*", line)
                    if findState:
                        stateCount += 1
                        stateName = findState.groups()[0]
                        stateNameToID[stateName] = stateCount - 1
                        stateIDToName[stateCount - 1] = stateName
    logger.info(f"Found {stateCount} states in state_regions")
    stateInfo = [0] * stateCount
    for s in range(stateCount):
        stateInfo[s] = {'naval_exit_id': 0, 'resourcesStaticTotal': 0}
    return stateCount, stateInfo, stateNameToID, stateIDToName

def getResourcesFromConfig(stateCount, logger):
    resources = {}
    countResStatic = 0
    countResDynamic = 0
    fileName = "resources.ini"
    if not os.path.exists(fileName):
        logger.error("File resource.txt does not exist")
        exit
    with open(fileName, "r") as f:
        for line in f:
            isDynamic = re.search(r"dynamic", line)
            noInitialBuildings = re.search(r'noInitialBuildings', line)
            findResource = re.search(r"([a-z0-9]+)\s+([_\w]+)\s+([_\w]+)\s+([_\w]+)", line)
            if findResource == None:
                logger.error(f"Error parsing line {line} in {fileName}")
            else:
                name = findResource.groups()[0]
                color = findResource.groups()[1] 
                bg = findResource.groups()[2]
                b = findResource.groups()[3]
                objectToAdd = {
                    'buildingGroup': bg, 
                    'building': b, 
                    'available': [0] * stateCount,
                    'isDynamic': isDynamic,
                    'discoveredInState': [0] * stateCount,
                    'undiscoveredInState': [0] * stateCount,
                    "isShuffled": False,
                    "noInitialBuildings": noInitialBuildings,
                    'constrainedHistory': [0] * stateCount,
                    'constrainedCompany': [0] * stateCount,
                    'constrainedHistoryTotal': 0,
                    'constrainedCompanyTotal': 0,
                    'total' : 0,
                    'totalDiscovered' : 0,
                    'totalUndiscovered' : 0,
                    'stringVar': None,
                    'strColor': color
                    }
                resources[name] = objectToAdd
                if isDynamic:
                    countResStatic += 1
                else:
                    countResDynamic += 1
        
    logger.info(f"Loaded {countResStatic} static resources and {countResDynamic} dynamic resources")

    return resources

def trimStateRegions(pathGameStateRegions, logger):
    tempFileLocation = "temp.txt"
    lineCount = 0
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            with open(filePath, "r") as f, open(tempFileLocation, "w") as g:
                lines = f.readlines()
                willNotWritePersistent = False
                for line in lines:
                    if not willNotWritePersistent:
                        willWrite = True
                    if re.search(r'capped_resources', line) or re.search('resource = {', line):
                        willWrite = False
                        willNotWritePersistent = True
                    if re.search(r'^}$', line):
                        willWrite = True
                        willNotWritePersistent = False
                    if willWrite:
                        g.write(line)
            with open(tempFileLocation, "r") as g:
                lines = g.readlines()
                lineCount += len(lines)
            shutil.copy2(tempFileLocation, filePath)
    os.remove(tempFileLocation)
    logger.info(f"Total lines in trimmed state_regions: {lineCount}")

def shuffleResources(resources, logger, stateIDToName):
    
    # remove guaranteed resources
    for resKey, resource in resources.items():
        if resKey in resourcesToIgnore:
            continue
        if not resource['isShuffled']:
            continue
        for state, _ in enumerate(resource['available']):
            constrHistory = resource['constrainedHistory'][state]
            constrCompany = resource['constrainedCompany'][state]
            protectedAvailability = max(constrHistory, constrCompany)                
            if protectedAvailability > 0:
                if resource['noInitialBuildings']:
                    resource['undiscoveredInState'][state] = max(0, resource['undiscoveredInState'][state] - protectedAvailability)
                else:
                    if resource['available'][state] < protectedAvailability:
                        logger.info(f'Not enough {str(resKey)} in {stateIDToName[state]}: {str(resource['available'][state])} for initial buildings: {str(constrHistory)} + company: {str(constrCompany)}')
                    
                    resource['available'][state] = max(0, resource['available'][state] - protectedAvailability)

    # shuffle remaining resources
    for resKey, resource in resources.items():
        if resKey in resourcesToIgnore:
            continue
        if resource['isShuffled'] == False:
            continue
        shuffle(resource['available'])
        if resource['isDynamic']:
            for resKey, resource in resources.items():
                if resource['totalDiscovered'] > 0:
                    shuffle(resource['discoveredInState'])
                if resource['totalUndiscovered'] > 0:
                    shuffle(resource['undiscoveredInState'])
                        
    # restore guaranteed resources
    for resKey, resource in resources.items():
        if resKey in resourcesToIgnore:
            continue
        if not resource['isShuffled']:
            continue
        for state, _ in enumerate(resource['available']):
            constrHistory = resource['constrainedHistory'][state]
            constrCompany = resource['constrainedCompany'][state]
            protectedAvailability = max(constrHistory, constrCompany)
            if protectedAvailability > 0:
                if resource['noInitialBuildings']:
                    resource['undiscoveredInState'][state] += protectedAvailability
                else:
                    resource['available'][state] += protectedAvailability
    
	#check
    for resKey, resource in resources.items():
        if resKey in resourcesToIgnore:
            continue
        if not resource['isShuffled']:
            continue
        for state, _ in enumerate(resource['available']):
            constrHistory = resource['constrainedHistory'][state]
            constrCompany = resource['constrainedCompany'][state]
            protectedAvailability = max(constrHistory, constrCompany)                
            if protectedAvailability > 0:
                if resource['noInitialBuildings']:
                    if resource['undiscoveredInState'][state] < protectedAvailability:
                        logger.error(f'Not enough undiscovered {str(resKey)} in {stateIDToName[state]}: {str(resource['available'][state])} for initial buildings: {str(constrHistory)} + company: {str(constrCompany)}')
                else:
                    if resource['available'][state] < protectedAvailability:
                        logger.error(f'Not enough available {str(resKey)} in {stateIDToName[state]}: {str(resource['available'][state])} for initial buildings: {str(constrHistory)} + company: {str(constrCompany)}')
                    
                    resource['available'][state] = max(0, resource['available'][state] - protectedAvailability)

def restoreStateRegions(pathGameStateRegions, stateInfo, resources, logger):
    tempFileLocation = "temp.txt"
    lineCount = 0
    stateCurrent = -1
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            with open(filePath, "r") as f, open(tempFileLocation, "w") as g:
                lines = f.readlines()
                for line in lines:
                    if re.search("(STATE_.*) =.*", line):
                        stateCurrent += 1
                    if re.search("^}$", line): # if found end of state info, restore
                        if stateInfo[stateCurrent]['resourcesStaticTotal'] > 0:
                            g.write('    capped_resources = {\n')
                            for key, resource in resources.items():
                                currentRes = resource['available'][stateCurrent]
                                if currentRes > 0:
                                    g.write('        ' + resource['buildingGroup'] + ' = ' + str(currentRes) + "\n")
                            g.write('    }\n')
                        for key, resource in resources.items():
                            resDisc = resource['discoveredInState'][stateCurrent]
                            resUndisc = resource['undiscoveredInState'][stateCurrent]
                            if resDisc + resUndisc > 0:
                                if resDisc * resUndisc > 0:
                                    pass #print('hi')
                                g.write('    resource = {\n')
                                g.write('        type = "' + resource['buildingGroup'] + '"\n')
                                if key == 'gold':
                                    g.write('        depleted_type = "bg_gold_mining"\n')
                                if resDisc > 0:
                                    g.write('        discovered_amount = ' + str(resDisc) + '\n')
                                if resUndisc > 0:
                                    g.write('        undiscovered_amount = ' + str(resUndisc) + '\n')
                                g.write('    }\n')
                        navalID = stateInfo[stateCurrent]['naval_exit_id']
                        if navalID > 0:
                            g.write('    naval_exit_id = ' + str(navalID) + '\n')
                    g.write(line)
            with open(tempFileLocation, "r") as g:
                lines = g.readlines()
                lineCount += len(lines)
            shutil.copy2(tempFileLocation, filePath)
    os.remove(tempFileLocation)
    logger.info(f"Total lines in restored state_regions: {lineCount}")


def clearCollectedResources(stateCount, resources):
    for resourceName, resource in resources.items():
        resource['available'] = [0] * stateCount
        resource['discoveredInState'] = [0] * stateCount
        resource['undiscoveredInState'] = [0] * stateCount
        resource['constrainedHistory'] = [0] * stateCount
        resource['constrainedCompany'] = [0] * stateCount
        resource['constrainedHistoryTotal'] = 0
        resource['constrainedCompanyTotal'] = 0
        resource['total'] = 0
        resource['totalDiscovered'] = 0
        resource['totalUndiscovered'] = 0

def getVersions(pathAppdataVersions, logger) -> List:
    versions = []
    if os.path.exists(os.path.join(pathAppdataVersions, "original")):
        versions.append("original")
    for name in os.listdir(pathAppdataVersions):
        if name == "original":
            continue
        if os.path.isdir(os.path.join(pathAppdataVersions, name)):
            versions.append(name)
    logger.info(f"Loaded {len(versions)} versions")
    return versions