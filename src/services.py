import os
from random import shuffle
import re
import shutil
import sys
from typing import List
from globalProperties import IGNORED_RESOURCES
from Auxiliary import copyTree

def backUpStateRegions(pathGameStateRegions, pathAppdataStateRegionsOriginal, logger):
    """If there is no back-up on %appdata%, create it
    Otherwise, replace the game's files with the back-up, to start fresh"""
    if not os.path.exists(pathAppdataStateRegionsOriginal):
        os.makedirs(pathAppdataStateRegionsOriginal)
        copyTree(pathGameStateRegions, pathAppdataStateRegionsOriginal)
        logger.info("Made a back-up from %appdata%")
    else:
        copyTree(pathAppdataStateRegionsOriginal, pathGameStateRegions)
        logger.info("Game's state_region replaced by the back-up from %appdata%")

def getGameFilePaths(pathGame, pathAppdataStateRegionsOriginal, logger):
    """Check if the provided path to the game is correct. 
    If that's the case, return paths to folders that are worked with by the app, such as the state regions, history buildings, companies and good icons"""
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

    backUpStateRegions(pathGameStateRegions, pathAppdataStateRegionsOriginal, logger)
    
    return validPath, pathGame, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, pathGameGoodIcons

def getStateCountAndNames(pathGameStateRegions, logger):
    """Get the number & names of states
    This must be done before running the methods that read from state regions, buildings and history"""
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
    """Extracts from 'resources.ini' the list of: resource name, the corresponding building, the corresponding building group, whether it's dynamic, whether it's hidden at the beggining of the game (& no buildings using it), GUI color
    
    It is necessary to perform any reading from game files
    """
    resources = {}
    countResStatic = 0
    countResDynamic = 0
    fileName = "resources.ini"
    if not os.path.exists(fileName):
        logger.error("File resource.txt does not exist")
        sys.exit()
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
                    'strColor': color,
                    'bestStates': [],
                    'biggestValues': [],
                    'labelBestStates': None,
                    }
                resources[name] = objectToAdd
                if isDynamic:
                    countResStatic += 1
                else:
                    countResDynamic += 1
        
    logger.info(f"Loaded {countResStatic} static resources and {countResDynamic} dynamic resources")

    return resources

def updateNewStateRegions(pathGameStateRegions, stateInfo, resources, logger, stateIDToName) -> List:
    """Remove old changes, Shuffle, add new changes"""
    trimStateRegions(pathGameStateRegions, logger)
    resources = shuffleResources(resources, logger, stateIDToName)
    restoreStateRegions(pathGameStateRegions, stateInfo, resources, logger)
    return resources

def trimStateRegions(pathGameStateRegions, logger) -> None:
    """So that changes are made in the state_regions, firstly elements will be removed from the files"""
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

def shuffleResources(resources, logger, stateIDToName) -> List:
    """Shuffles resources - for each resource to be shuffled: it removes from each state the guaranteed amount, shuffles the new list, then it adds the guaranteed amount back
    
    Guaranteed amount of resources = Quantity of resources prepared for initial buildings and companies, so that they are useable"""
    # remove guaranteed resources

    for resKey, resource in resources.items():
        if resKey in IGNORED_RESOURCES:
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
        if resKey in IGNORED_RESOURCES:
            continue
        if resource['isShuffled'] == False:
            continue
        shuffle(resource['available'])
        if resource['totalDiscovered'] > 0:
            shuffle(resource['discoveredInState'])
        if resource['totalUndiscovered'] > 0:
            shuffle(resource['undiscoveredInState'])

    # restore guaranteed resources
    for resKey, resource in resources.items():
        if resKey in IGNORED_RESOURCES:
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
        if resKey in IGNORED_RESOURCES:
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
    return resources

def restoreStateRegions(pathGameStateRegions, stateInfo, resources, logger) -> None:
    """Add the shuffled amount of resources to the files (state_regions)"""
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
    """Remove the collected information about resources, such as available, discovered, undiscovered, guaranteed quantity and best states"""
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
        resource['bestStates'] = []
        resource['biggestValues'] = []

def getVersions(pathAppdataVersions, logger) -> List:
    """Get from %appdata% the list of folders representing the versions, so that it will be loaded into a combobox"""
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

def findStatesWithMostResources(resources, stateCount) -> List:
    """Find state with the most resources
    It is necessary to have run the method 'getInfoFromStateRegions'"""
    for key, resource in resources.items():
        for state in range(stateCount):
            currentSum = resource['available'][state] + resource['discoveredInState'][state] + resource['undiscoveredInState'][state]
            resource['bestStates'].append(state)
            resource['biggestValues'].append(currentSum)

        pairs = list(zip(resource['bestStates'], resource['biggestValues']))
        sorted_pairs = sorted(pairs, key=lambda x: x[1], reverse=True)
        
        resource['bestStates'], resource['biggestValues'] = zip(*sorted_pairs)
        resource['bestStates'] = resource['bestStates'][:5]
        resource['biggestValues'] = resource['biggestValues'][:5]
    return resources

def loadVersionConfigFile(app, pathAppdataVersions):
    """Gets the list of shuffled resources for the current version
    The version must be selected from the combobox in the app"""
    currentVersion = app.comboBoxVersions.get()
    filePath = os.path.join(pathAppdataVersions, currentVersion, 'config.ini')
    if not os.path.exists(filePath):
        for resKey, resource in app.resources.items():
            if resKey in IGNORED_RESOURCES:
                continue
            resource['stringVar'].set("0")
    else:
        with open(filePath, "r") as f:
            line = f.readline()
            goods = line.split(' ')
            goods = goods[:len(goods) - 1]
            for resKey, resource in app.resources.items():
                if resKey in IGNORED_RESOURCES:
                    continue
                resource['stringVar'].set("0")
                for good in goods:
                    if good == resKey:
                        resource['stringVar'].set("1")
                        break
    