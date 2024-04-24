import os
import re
import sys
from StateResourceExpected import StateResourceExpected
from globalProperties import logger

def getInfoFromStateRegions(pathGameStateRegions, stateInfo, resources, logger):
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

def getResourcesFromHistory(pathGameHistoryBuildings, resources, logger):
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

def getResourcesFromCompanies(stateNameToID, stateIDToName, resources, pathGameCompanies, logger):
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