import os, shutil
import logging.config
import logging.handlers
import sys
import yaml
import re
from enum import Enum

class StateResourceExpected (Enum):
    NONE = 0
    STATIC = 1
    DYNAMIC = 2

def copyTree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def setupLogging():
    configFile = pathAppdataStateRegions = os.path.join("loggingConfigs", "config.yaml")
    with open(configFile) as fIn:
        config = yaml.safe_load(fIn)
    logging.config.dictConfig(config)

    logger = logging.getLogger("V3RS")
    logging.basicConfig(level="INFO")

    return logger

def configureAppData():
    pathAppdata = os.path.join(os.getenv('APPDATA'), "Victoria 3 Resource Shuffler")
    pathAppdataStateRegions = os.path.join(pathAppdata, "state_regions")
    pathAppdataStateRegionsOriginal = os.path.join(pathAppdataStateRegions, "original")

    pathAppdataConfig = os.path.join(pathAppdata, "config.txt")
    if not os.path.exists(pathAppdataStateRegions):
        os.makedirs(pathAppdataStateRegions)

    # Does path exist in config?
    pathGame = None
    if not os.path.exists(pathAppdataConfig):
        with open(pathAppdataConfig, "a+") as f:
            f.write("path=")
        logger.error("Config does not exist in %appdata%. It has been created now. Please input the path to the game")
        exit

    with open(pathAppdataConfig, "r") as f:
        for line in f:
            if pathGame is None:
                pathGame = re.search("path=(.*)", line)
        if pathGame is None:
            logger.error("Path not defined")
        else:
            pathGame = pathGame.groups()[0]


    pathGameStateRegions = os.path.join(pathGame, "game", "map_data", "state_regions")
    if not os.path.exists(pathGame):
        logger.error("Path to Victoria 3 folder does not exist in config file")
        exit
    if not os.path.exists(pathGameStateRegions):
        logger.error("Path does not correspond to Victoria 3 folder")
        exit
    
    #backup
    if not os.path.exists(pathAppdataStateRegionsOriginal):
        os.makedirs(pathAppdataStateRegionsOriginal)
        copyTree(pathGameStateRegions, pathAppdataStateRegionsOriginal)
        logger.info("Made a back-up from %appdata%")
    else:
        copyTree(pathAppdataStateRegionsOriginal, pathGameStateRegions)
        logger.info("Game's state_region replaced by the back-up from %appdata%")
    
    return pathAppdataStateRegions, pathGameStateRegions

def getStatesInfo():
    states = 0
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            with open(filePath, "r") as f:
                for line in f:
                    findState = re.search("(STATE_.*) =.*", line)
                    if findState:
                        states += 1
    logger.info(f"Found {states} states in state_regions")
    stateInfo = [0] * states
    for s in range(states):
        stateInfo[s] = {'naval_exit_id': 0, 'resourcesStatic': 0}
    return states, stateInfo

def getResources(stateCount, stateInfo):
    resourcesStatic = {}
    resourcesDynamic = {}
    countResStatic = 0
    countResDynamic = 0
    state = "static"
    fileName = "resources.ini"
    if not os.path.exists(fileName):
        logger.error("File resource.txt does not exist")
        exit
    with open(fileName, "r") as f:
        for line in f:
            if re.search(r"# static", line):
                state = "static"
            elif re.search(r"# dynamic", line):
                state = "dynamic"
            elif state == "static":
                findResource = re.search(r"([_\w]+)\s+([_\w]+)\s+([_\w]+)", line)
                if findResource == None:
                    logger.error(f"Error parsing line {line} in {fileName}")
                else:
                    name = findResource.groups()[0]
                    b = findResource.groups()[1]
                    c = findResource.groups()[2]
                    objectToAdd = {'buildingGroup': b, 
                                   'building': c, 
                                   'states': [0] * stateCount,
                                   'total' : 0
                                   }
                    resourcesStatic[name] = objectToAdd
                    countResStatic += 1
            elif state == "dynamic":
                findResource = re.search(r"([_\w]+)\s+([_\w]+)", line)
                if findResource == None:
                    logger.error(f"Error parsing line {line} in {fileName}")
                else:
                    name = findResource.groups()[0]
                    b = findResource.groups()[1]
                    objectToAdd = {'buildingGroup': b, 
                                   'discoveredInState': [0] * stateCount,
                                   'undiscoveredInState': [0] * stateCount,
                                   'totalDiscovered' : 0,
                                   'totalUndiscovered' : 0
                                   }
                    resourcesDynamic[name] = objectToAdd
                    countResDynamic += 1

    logger.info(f"Loaded {countResStatic} static resources and {countResDynamic} dynamic resources")

    return resourcesStatic, resourcesDynamic

def getInfoFromStateRegions(resourcesStatic):
    logger.info(f"Reading files from {pathGameStateRegions}")
    resourcesFoundStatic = 0
    resourcesFoundDiscovered = 0
    resourcesFoundUndiscovered = 0
    stateCurrent = -1
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            logger.info(f"Reading state_region {filename}")
            with open(filePath, "r") as f:
                lines = f.readlines()
                state = StateResourceExpected.NONE
                for lineID in range(len(lines)):
                    line = lines[lineID]
                    found = re.search("(STATE_.*) =.*", line)
                    if found:
                        stateCurrent += 1
                        state = StateResourceExpected.NONE
                        continue
                    elif re.search("capped_resources", line):
                        state = StateResourceExpected.STATIC
                        continue
                    elif re.search("resource =", line):
                        state = StateResourceExpected.DYNAMIC
                        continue
                    
                    found = re.search(r"naval_exit_id\s*=\s*(\d+)", line)
                    if found:
                        stateInfo[stateCurrent]["naval_exit_id"] = int(found.groups()[0])
                    if state == StateResourceExpected.STATIC:                        
                        for key, resource in resourcesStatic.items():
                            findResource = re.search(resource['buildingGroup'] + r" = (\d+)", line)
                            if findResource:
                                value = int(findResource.groups()[0])
                                resource['states'][stateCurrent] = value
                                resource['total'] += value
                                stateInfo[stateCurrent]['resourcesStatic'] += value
                                resourcesFoundStatic += value
                    elif state == StateResourceExpected.DYNAMIC:
                        for key, resource in resourcesDynamic.items():
                            findResource = re.search(r'type\s*=\s*"' + resource['buildingGroup'], line)
                            if findResource:
                                while(not re.search('    }', line)):
                                    lineID += 1
                                    line = lines[lineID]
                                    findResource = re.search(r'        discovered_amount = (\d+)', line)
                                    if findResource:
                                        value = int(findResource.groups()[0])
                                        resource['discoveredInState'][stateCurrent] = value
                                        resource['totalDiscovered'] += value
                                        resourcesFoundDiscovered += value
                                        lineID += 1
                                        line = lines[lineID]
                                    findResource = re.search(r'        undiscovered_amount = (\d+)', line)
                                    if findResource:
                                        value = int(findResource.groups()[0])
                                        resource['undiscoveredInState'][stateCurrent] = value
                                        resource['totalUndiscovered'] += value
                                        resourcesFoundUndiscovered += value
                        
    if resourcesFoundStatic == 0:
        logger.error("No static resources found in state_regions")
        sys.exit()
    else:
        logger.info(f"Found {resourcesFoundStatic} static resources in state_regions")
        for key, resource in resourcesStatic.items():
            logger.info(f"Static: {resource['total']} {key} in state_regions")
    
    if resourcesFoundUndiscovered + resourcesFoundDiscovered == 0:
        logger.error("No dynamic resources found in state_regions")
        sys.exit()
    else:
        logger.info(f"Found {resourcesFoundDiscovered + resourcesFoundUndiscovered} dynamic resources in state_regions:")
        
        logger.info(f"Found {resourcesFoundDiscovered} discovered resources in state_regions:")
        if resourcesFoundDiscovered > 0:
            for key, resource in resourcesDynamic.items():
                logger.info(f"Discovered: {resource['totalDiscovered']} {key} in state_regions")
        
        logger.info(f"Found {resourcesFoundUndiscovered} undiscovered resources in state_regions:")
        if resourcesFoundUndiscovered > 0:
            for key, resource in resourcesDynamic.items():
                logger.info(f"Undiscovered: {resource['totalUndiscovered']} {key} in state_regions")
    
    return resourcesStatic, resourcesDynamic, stateInfo
                    
def trimStateRegions():
    tempFileLocation = "temp.txt"
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            logger.info(f"Reading state_region {filename}")
            with open(filePath, "r") as f, open(tempFileLocation, "w") as g:
                lines = f.readlines()
                willNotWritePersistent = False
                for line in lines:
                    if not willNotWritePersistent:
                        willWrite = True
                    if re.search(r'capped_resources', line):
                        willWrite = False
                        willNotWritePersistent = True
                    if re.search(r'^}$', line):
                        willWrite = True
                        willNotWritePersistent = False
                    if willWrite:
                        g.write(line)
            shutil.copy2(tempFileLocation, filePath)
    os.remove(tempFileLocation)

def shuffle():
    pass

def restoreStateRegions():
    tempFileLocation = "temp.txt"
    stateCurrent = -1
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            logger.info(f"Reading state_region {filename}")
            with open(filePath, "r") as f, open(tempFileLocation, "w") as g:
                lines = f.readlines()
                for line in lines:
                    if re.search("(STATE_.*) =.*", line):
                        stateCurrent += 1
                    if re.search("^}$", line): # if found end of state info, restore
                        if stateInfo[stateCurrent]['resourcesStatic'] > 0:
                            g.write('    capped_resources = {\n')
                            for key, resource in resourcesStatic.items():
                                currentRes = resource['states'][stateCurrent]
                                if currentRes > 0:
                                    g.write('        ' + resource['buildingGroup'] + ' = ' + str(currentRes) + "\n")
                            g.write('    }\n')
                        for key, resource in resourcesDynamic.items():
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
            shutil.copy2(tempFileLocation, filePath)
    os.remove(tempFileLocation)

if __name__ == "__main__":
    logger = setupLogging()
    pathAppdataStateRegions, pathGameStateRegions = configureAppData()
    countStates, stateInfo = getStatesInfo()
    resourcesStatic, resourcesDynamic = getResources(countStates, stateInfo)
    resourcesStatic, resourcesDynamic, stateInfo = getInfoFromStateRegions(resourcesStatic)
    trimStateRegions()
    shuffle()
    restoreStateRegions()
