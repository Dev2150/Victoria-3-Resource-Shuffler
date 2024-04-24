from DialogApp import App
from Logging import setupLogging
from AppData import configureAppData

if __name__ == "__main__":
    logger = setupLogging()
    pathAppdataVersions, pathAppdataConfig, pathAppdataStateRegionsOriginal = configureAppData(logger)

    app = App(pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions)
    app.mainloop()

