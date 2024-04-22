import os, shutil
import logging.config
import logging.handlers
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

def getStateCount():
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
    return states

def getResourceKit(stateCount):
    resourceKitStatic = {}
    resourceKitDynamic = {}
    state = None
    fileName = "resources.ini"
    if not os.path.exists(fileName):
        logger.error("File resource.txt does not exist")
        exit
    with open(fileName, "r") as f:
        for line in f:
            if line == "# static\n":
                state = "static"
            elif line == "# dynamic\n":
                state = "dynamic"
            elif state == "static":
                findResource = re.search(r"([_\w]+)\s+([_\w]+)\s+([_\w]+)", line)
                if findResource == None:
                    logger.error(f"Error parsing line {line} in {fileName}")
                else:
                    name = findResource.groups()[0]
                    b = findResource.groups()[1]
                    c = findResource.groups()[2]
                    logger.info(f"{name} {b} {c}")
                    objectToAdd = {'buildingGroup': b, 
                                        'building': c, 
                                        'states': [0] * stateCount}
                    resourceKitStatic[name] = objectToAdd
            elif state == "dynamic":
                findResource = re.search(r"([_\w]+)\s+([_\w]+)", line)
                if findResource == None:
                    logger.error(f"Error parsing line {line} in {fileName}")
                else:
                    name = findResource.groups()[0]
                    b = findResource.groups()[1]
                    logger.info(f"{name} {b}")
                    objectToAdd = {'buildingGroup': b, 
                                   'statesDiscovered': [0] * stateCount,
                                   'statesUndiscovered': [0] * stateCount}
                    resourceKitDynamic[name] = objectToAdd

    return resourceKitStatic, resourceKitDynamic

def getResourcesFromStateRegions(resourceKitStatic, pathGameStateRegions):
    logger.info(f"Reading files from {pathGameStateRegions}")
    resourcesFound = 0
    stateCurrent = -1
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            logger.info(f"Reading state_region {filename}")
            with open(filePath, "r") as f:
                state = StateResourceExpected.NONE
                for line in enumerate(f):
                    findState = re.search("(STATE_.*) =.*", line)
                    if findState:
                        stateCurrent += 1
                        state = StateResourceExpected.NONE
                        continue
                    findState = re.search("capped_resources", line)
                    if findState:
                        state = StateResourceExpected.STATIC
                        continue
                    findState = re.search("resource =", line)
                    if findState:
                        state = StateResourceExpected.DYNAMIC
                        continue
                    
                    if state == StateResourceExpected.STATIC:                        
                        for idR, resource in enumerate(resourceKitStatic):
                            findResource = re.search(resource['buildingGroup'] + r" = (\d+)", line)
                            if findResource:
                                value = int(findResource.groups()[0])
                                resourceKitStatic[idR]['states'][stateCurrent] = value
                                resourcesFound += value
                    elif state == StateResourceExpected.DYNAMIC:

                        pass
    
    logger.info(f"Found {resourcesFound} resources in state_regions")
    return resourceKitStatic
                    
                        


if __name__ == "__main__":
    logger = setupLogging()
    pathAppdataStateRegions, pathGameStateRegions = configureAppData()
    countStates = getStateCount()
    resourceKitStatic, resourceKitDiscovered, resourceKitUndiscovered = getResourceKit(countStates)
    resourceKitStatic = getResourcesFromStateRegions(resourceKitStatic, pathGameStateRegions)
