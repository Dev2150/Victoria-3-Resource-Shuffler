import functools
import os, shutil
import logging.config
import logging.handlers
import sys
import yaml
import re
from random import shuffle
from enum import Enum
import customtkinter
from PIL import Image

class StateResourceExpected (Enum):
    NONE = 0
    STATIC = 1
    DYNAMIC = 2

resourcesToIgnore = ['monument', 'fish', 'whale']
global resourcesListGUI
resourcesListGUI = []

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
    logger.info("Logger ready")
    return logger

def configureAppData():
    pathAppdata = os.path.join(os.getenv('APPDATA'), "Victoria 3 Resource Shuffler")
    pathAppdataStateRegions = os.path.join(pathAppdata, "state_regions")
    pathAppdataStateRegionsOriginal = os.path.join(pathAppdataStateRegions, "original")

    pathAppdataConfig = os.path.join(pathAppdata, "config.txt")
    if not os.path.exists(pathAppdataStateRegions):
        os.makedirs(pathAppdataStateRegions)

    if not os.path.exists(pathAppdataConfig):
        with open(pathAppdataConfig, "a+") as f:
            f.write("path=")
        logger.error("Config does not exist in %appdata%. It has been created now. Please input the path to the game")
        sys.exit()
    return pathAppdataStateRegions, pathAppdataConfig, pathAppdataStateRegionsOriginal

def makeBackUp(pathGameStateRegions):
    if not os.path.exists(pathAppdataStateRegionsOriginal):
        os.makedirs(pathAppdataStateRegionsOriginal)
        copyTree(pathGameStateRegions, pathAppdataStateRegionsOriginal)
        logger.info("Made a back-up from %appdata%")
    else:
        copyTree(pathAppdataStateRegionsOriginal, pathGameStateRegions)
        logger.info("Game's state_region replaced by the back-up from %appdata%")

def configureGamePath(path):
    # Does path exist in config?
    pathGame = path
    validPath = True

    pathGameStateRegions = os.path.join(pathGame, "game", "map_data", "state_regions")
    pathGameHistoryBuildings = os.path.join(pathGame, "game", "common", "history", "buildings")
    pathGameCompanies = os.path.join(pathGame, "game", "common", "company_types")
    pathGameGoodIcons = os.path.join(pathGame, "game", "gfx", "interface", "icons", "goods_icons")
    if not os.path.exists(pathGame):
        #logger.error("Path to Victoria 3 folder does not exist in config file")
        validPath = False
    if not os.path.exists(pathGameStateRegions):
        #logger.error(f"Path does not correspond to Victoria 3 folder; Expected {pathGameStateRegions}")
        validPath = False
    if not os.path.exists(pathGameHistoryBuildings):
        #logger.error(f"Path does not correspond to Victoria 3 folder; Expected {pathGameHistoryBuildings}")
        validPath = False
    if not os.path.exists(pathGameCompanies):
        #logger.error(f"Path does not correspond to Victoria 3 folder; Expected {pathGameCompanies}")
        validPath = False
    
    if not validPath:
        return validPath, None, None, None, None

    makeBackUp(pathGameStateRegions)
    
    return validPath, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, pathGameGoodIcons

def getStatesInfo():
    states = 0
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
                        states += 1
                        stateName = findState.groups()[0]
                        stateNameToID[stateName] = states - 1
                        stateIDToName[states - 1] = stateName
    logger.info(f"Found {states} states in state_regions")
    stateInfo = [0] * states
    for s in range(states):
        stateInfo[s] = {'naval_exit_id': 0, 'resourcesStaticTotal': 0}
    return states, stateInfo, stateNameToID, stateIDToName

def getResourcesFromConfig(stateCount):
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
            findResource = re.search(r"([_\w]+)\s+([_\w]+)\s+([_\w]+)", line)
            if findResource == None:
                logger.error(f"Error parsing line {line} in {fileName}")
            else:
                name = findResource.groups()[0]
                bg = findResource.groups()[1]
                b = findResource.groups()[2]
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
                    'stringVar': None
                    }
                resources[name] = objectToAdd
                if isDynamic:
                    countResStatic += 1
                else:
                    countResDynamic += 1
        
    logger.info(f"Loaded {countResStatic} static resources and {countResDynamic} dynamic resources")

    return resources

def getInfoFromStateRegions():
    logger.info(f"Reading files from {pathGameStateRegions}")
    resourcesFoundStatic = 0
    resourcesFoundDiscovered = 0
    resourcesFoundUndiscovered = 0
    lineCount = 0
    stateCurrent = -1
    for filename in os.listdir(pathGameStateRegions):
        if filename[0:2] == "99":
            continue
        filePath = os.path.join(pathGameStateRegions, filename)
        if os.path.isfile(filePath):
            with open(filePath, "r") as f:
                lines = f.readlines()
                lineCount += len(lines)
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
                        for key, resource in resources.items():
                            findResource = re.search(resource['buildingGroup'] + r" = (\d+)", line)
                            if findResource:
                                value = int(findResource.groups()[0])
                                resource['available'][stateCurrent] = value
                                resource['total'] += value
                                stateInfo[stateCurrent]['resourcesStaticTotal'] += value
                                resourcesFoundStatic += value
                    elif state == StateResourceExpected.DYNAMIC:
                        for key, resource in resources.items():
                            if not resource['isDynamic']:
                                continue
                            findResource = re.search(r'type\s*=\s*"' + resource['buildingGroup'], line)
                            if findResource:
                                while(not re.search('    }', line)):
                                    lineID += 1
                                    line = lines[lineID]
                                    findResource = re.search(r'        discovered_amount = (\d+)', line)
                                    if findResource:
                                        value = int(findResource.groups()[0])
                                        resource['discoveredInState'][stateCurrent] = value
                                        resources[key]['totalDiscovered'] += value
                                        resourcesFoundDiscovered += value
                                        lineID += 1
                                        line = lines[lineID]
                                    findResource = re.search(r'        undiscovered_amount = (\d+)', line)
                                    if findResource:
                                        value = int(findResource.groups()[0])
                                        resource['undiscoveredInState'][stateCurrent] = value
                                        resources[key]['totalUndiscovered'] += value
                                        resourcesFoundUndiscovered += value
                        
    if resourcesFoundStatic == 0:
        logger.error("No static resources found in state_regions")
        sys.exit()
    else:
        logger.info(f"Found {resourcesFoundStatic} static resources in state_regions")
        for key, resource in resources.items():
            logger.info(f"Static: {resource['total']} {key} in state_regions")
    
    if resourcesFoundUndiscovered + resourcesFoundDiscovered == 0:
        logger.error("No dynamic resources found in state_regions")
        sys.exit()
    else:
        logger.info(f"Found {resourcesFoundDiscovered + resourcesFoundUndiscovered} dynamic resources in state_regions:")
        
        logger.info(f"Found {resourcesFoundDiscovered} discovered resources in state_regions:")
        if resourcesFoundDiscovered > 0:
            for key, resource in resources.items():
                logger.info(f"Discovered: {resource['totalDiscovered']} {key} in state_regions")
        
        logger.info(f"Found {resourcesFoundUndiscovered} undiscovered resources in state_regions:")
        if resourcesFoundUndiscovered > 0:
            for key, resource in resources.items():
                logger.info(f"Undiscovered: {resource['totalUndiscovered']} {key} in state_regions")
    
    logger.info(f"Total lines in original state_regions: {lineCount}")
    return resources, stateInfo

def getResourcesFromHistory():
    logger.info(f"Reading files from {pathGameHistoryBuildings}")
    stateCurrent = -1
    for filename in os.listdir(pathGameHistoryBuildings):
        filePath = os.path.join(pathGameHistoryBuildings, filename)
        if os.path.isfile(filePath):
            with open(filePath, "r") as f:
                lines = f.readlines()
                for lineID in range(len(lines)):
                    line = lines[lineID]
                    found = re.search("(STATE_.*) =.*", line)
                    if found:
                        stateCurrent += 1
                    found = re.search(r'building="([a-z_]+)"', line)
                    if found:
                        building = found.groups()[0]
                        for key, resource in resources.items():
                            if resource['building'] == building:
                                lineID += 1
                                line = lines[lineID]
                                found = re.search(r'level=(\d+)', line)
                                if found:
                                    levels = int(found.groups()[0])
                                    resource['constrainedHistory'][stateCurrent] = levels
                                    resource['constrainedHistoryTotal'] += levels
                                else:
                                    logger.error(f'Expected resource for state #{stateCurrent} for building {resource['building']}')
                                    sys.exit()

    for key, resource in resources.items():
        logger.info(f"Initial buildings related to {key}: {resource['constrainedHistoryTotal']}")
    return resources

def getResourcesFromCompanies(stateNameToID, stateIDToName):
    logger.info(f"Reading files from {pathGameCompanies}")
    for filename in os.listdir(pathGameCompanies):
        filePath = os.path.join(pathGameCompanies, filename)
        if filename[0:2] != "00":
            continue
        if os.path.isfile(filePath):
            with open(filePath, "r", encoding="utf8") as f:
                lines = f.readlines()
                for lineID in range(len(lines)):
                    line = lines[lineID]
                    if re.search(r"possible\s*=\s*{", line):
                        listCandidateStates = []
                        listResourcesReq = []
                        #logger.debug(r"Reset - new company")
                        levelFound = False
                        while(not levelFound):
                            lineID += 1
                            line = lines[lineID]
                            found = re.search(r'state_region = s:([A-Z_]+)', line)
                            if found:
                                stateID = int(stateNameToID[found.groups()[0]])
                                listCandidateStates.append(stateID)
                                #logger.debug(f'{stateIDToName[stateID]} added to list of candidates')
                                continue
                            
                            found = re.search(r'is_building_type = ([a-z_]+)', line)
                            if found:
                                building = found.groups()[0]
                                for key, resource in resources.items():
                                    if building == resource['building']:
                                        listResourcesReq.append(key)
                                        logger.debug(f'#{key} added to list of resources')
                                        break
                            found = re.search(r'level.*=\s*(\d+)', line)
                            if not found:\
                                found = re.search(r'count.*=\s*(\d+)', line)
                            if found:
                                levels = int(found.groups()[0])
                                if len(listResourcesReq) * listCandidateStates == 0:
                                    if len(listResourcesReq) == 0:
                                        logger.error('NO resources required for company')
                                        sys.exit()
                                    if len(listCandidateStates) == 0:
                                        logger.error('NO candidate states required for company')
                                        sys.exit()
                                for resKey in listResourcesReq:
                                    for stateID in listCandidateStates:
                                        logger.debug(f'{levels} {resKey} required in state {stateIDToName[stateID]}')
                                        resources[resKey]['constrainedCompany'][stateID] = levels
                                        resources[resKey]['constrainedCompanyTotal'] += levels
                                levelFound = True

    for key, resource in resources.items():
        if key == "monument":
            continue
        logger.info(f"{resource['constrainedCompanyTotal']} {key} required for companies")
    return resources

def trimStateRegions():
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

def shuffleResources(resources):
    
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
                if resource['discoveredInStateTotal'] > 0:
                    shuffle(resource['discoveredInState'])
                if resource['undiscoveredInStateTotal'] > 0:
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

def restoreStateRegions():
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

def switch_resource_callback(resKey, resource):
    def callback():
        value = resource['stringVar'].get()
        if value == "1":
            resources[resKey]['isShuffled'] = True
        else:
            resources[resKey]['isShuffled'] = False
        print(f'{resKey}: {resources[resKey]['isShuffled']}')
    return callback

def execute():
    global resources
    for key, resource in resources.items():
        print (f'{key}: {resource['isShuffled']}')
    
    makeBackUp(pathGameStateRegions)
    getStatesInfo()
    resources, stateInfo = getInfoFromStateRegions()
    resources = getResourcesFromHistory()
    resources = getResourcesFromCompanies(stateNameToID, stateIDToName)
    trimStateRegions()
    shuffleResources(resources)
    restoreStateRegions()

def updateBasedOnEntryPath(pathToGame):
    global isPathValid, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, countStates, stateInfo, stateNameToID, stateIDToName, resources
    global imageRaw, btn
    global resourcesListGUI
    isPathValid, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, pathGameGoodIcons = configureGamePath(pathToGame)
    

    for widget in resourcesListGUI:
        widget.destroy()
    resourcesListGUI = []
    if isPathValid:
        imageRaw = Image.open('resources/OK.png')
        btn.configure(image=customtkinter.CTkImage(imageRaw))

        countStates, stateInfo, stateNameToID, stateIDToName = getStatesInfo()
        resources = getResourcesFromConfig(countStates)

        labelPresets = customtkinter.CTkLabel(master=app, text="Presets", justify=customtkinter.RIGHT)
        labelPresets.grid(row = 1, column = 0)

        comboBoxPresets = customtkinter.CTkComboBox(app, values=["Vanilla", "Gold", "Yellow & Black Gold", "Mineable & Oil", "All but wood", "All"])
        comboBoxPresets.grid(row = 1, column = 1)

        labelHeaderResource = customtkinter.CTkLabel(master=app, text="Resource", justify=customtkinter.RIGHT)
        labelHeaderResource.grid(row = 2, column = 0)
        
        labelHeaderShuffle = customtkinter.CTkLabel(master=app, text="Shuffle?", justify=customtkinter.RIGHT)
        labelHeaderShuffle.grid(row = 2, column = 1)

        btnExecute = customtkinter.CTkButton(app, text = "Execute", corner_radius=32, command=execute)
        btnExecute.grid(row=1, column=6)

        resourcesListGUI.extend([labelPresets, comboBoxPresets, labelHeaderResource, labelHeaderShuffle, btnExecute])
        for resKey, resource in resources.items():
            if resKey in resourcesToIgnore:
                continue
            resource['stringVar'] = customtkinter.StringVar(value="0")
            #imageRaw = Image.open(os.path.join(pathGameGoodIcons, resKey + ".dds"))
            #imageRaw = imageRaw.resize((15, 15))
            label = customtkinter.CTkLabel(master=app, text="                        " + resKey.capitalize(), justify=customtkinter.RIGHT)
                                           #,image=customtkinter.CTkImage(imageRaw))
            label.grid(row = 3 + len(resourcesListGUI), column = 0)

            checkBox = customtkinter.CTkSwitch(master=app, text="", variable=resource['stringVar'], onvalue="1", offvalue="0",
                                               command=functools.partial(switch_resource_callback(resKey, resource)))
            checkBox.grid(row = 3 + len(resourcesListGUI), column = 1)
            resourcesListGUI.extend([label, checkBox])
    else:
        imageRaw = Image.open('resources/wrong.png')
        btn.configure(image=customtkinter.CTkImage(imageRaw))
def on_entry_changed(event):
    updateBasedOnEntryPath(entry1.get())

if __name__ == "__main__":
    logger = setupLogging()
    pathAppdataStateRegions, pathAppdataConfig, pathAppdataStateRegionsOriginal = configureAppData()

    app = customtkinter.CTk()
    app.geometry("1000x400")
    customtkinter.set_appearance_mode("System")
    customtkinter.set_appearance_mode("dark")
    width = 5
    for i in range(width+1):
        app.grid_columnconfigure(i, weight=1, uniform=5)

    pathGame = None
    with open(pathAppdataConfig, "r") as f:
        for line in f:
            pathGame = re.search("path=(.*)", line)
            if pathGame:
                pathGame = pathGame.groups()[0]
                break

    label = customtkinter.CTkLabel(master=app, text="Victoria 3 / Mod folder: ")
    label.grid(row=0, column=0, columnspan=2, padx=(10, 5), pady=10)#, sticky=customtkinter.W)

    entry1 = customtkinter.CTkEntry(master=app, width=500)
    entry1.insert(0, pathGame)
    entry1.grid(row=0, column=2, columnspan=4, padx=(0, 10), pady=10)#, sticky=customtkinter.W)
    entry1.bind("<KeyRelease>", on_entry_changed)
    imageRaw = Image.open('resources/wrong.png')
    #image = customtkinter.CTkImage(imageRaw)
    btn = customtkinter.CTkButton(app, text = "", corner_radius=32, fg_color="transparent", image=customtkinter.CTkImage(imageRaw))
    btn.grid(row=0, column=6)
    
    updateBasedOnEntryPath(pathGame)

    app.mainloop()

