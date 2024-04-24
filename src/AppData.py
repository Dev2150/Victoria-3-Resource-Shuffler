import os

def configureAppData(logger):
    pathAppdata = os.path.join(os.getenv('APPDATA'), "Victoria 3 Resource Shuffler")
    pathAppdataVersions = os.path.join(pathAppdata, "versions")
    pathAppdataStateRegionsOriginal = os.path.join(pathAppdataVersions, "original", "state_regions")

    pathAppdataConfig = os.path.join(pathAppdata, "config.txt")
    if not os.path.exists(pathAppdataVersions):
        os.makedirs(pathAppdataVersions)

    if not os.path.exists(pathAppdataConfig):
        with open(pathAppdataConfig, "a+") as f:
            f.write("path=")
        logger.info("Config does not exist in %appdata%. It has been created now. Please input the path to the game")
    return pathAppdataVersions, pathAppdataConfig, pathAppdataStateRegionsOriginal