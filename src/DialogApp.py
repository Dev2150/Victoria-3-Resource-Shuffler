import functools
import os
import sys
import customtkinter as ctk
from PIL import Image
import re
from callbacks import openFolderCallback, switchBestStatesCallback, switchResourceCallback, switchResourcePresetCallback, switchVersionCallback, execute
from globalProperties import IGNORED_RESOURCES, TEXT_DEFAULT_BEST_STATES, resourcesListGUI, extendedGUIElements, TABLE_GOODS_FIRST_ROW
from readFromGameFiles import getInfoFromStateRegions
from services import configureGamePath, findStatesWithMostResources, getResourcesFromConfig, getStatesInfo, getVersions

class App(ctk.CTk):
    def __init__(self, pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 5
        
        self.title("Victoria 3 Resource Shuffler")
        self.geometry("1200x400")
        ctk.set_appearance_mode("System")
        ctk.set_appearance_mode("dark")
        for i in range(self.width+1):
            self.grid_columnconfigure(i, weight=1, uniform=5)

        self.pathGame = None
        with open(pathAppdataConfig, "r") as f:
            for line in f:
                pathGame = re.search("path=(.*)", line)
                if pathGame:
                    pathGame = pathGame.groups()[0]
                    break

        self.labelPath = ctk.CTkLabel(master=self, text="Victoria 3 / Mod folder: ")
        self.labelPath.grid(row=0, column=0, columnspan=2, padx=(10, 5), pady=10)#, sticky=ctk.W)

        self.entryPath = ctk.CTkEntry(master=self, width=500)
        self.entryPath.insert(0, pathGame)
        self.entryPath.grid(row=0, column=2, columnspan=4, padx=(0, 10), pady=10)#, sticky=ctk.W)
        self.imagePathIsCorrect = Image.open('resources/wrong.png')
        self.btnPathIsCorrect = ctk.CTkButton(self, text = "", corner_radius=32, fg_color="transparent", image=ctk.CTkImage(self.imagePathIsCorrect))
        self.btnPathIsCorrect.grid(row=0, column=6)
        
        self.top = None
        self.entryPath.bind("<KeyRelease>", functools.partial(updateBasedOnEntryPath, self, pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions))
        updateBasedOnEntryPath(self, pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions, None)

def clearExtendedGUI():
    global resourcesListGUI, extendedGUIElements
    for widget in resourcesListGUI:
        widget.destroy()
    for widget in extendedGUIElements:
        widget.destroy()
    resourcesListGUI = []
    extendedGUIElements = []

def updateBasedOnEntryPath(app, pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions, event):
    def callback():
        pathToGame = app.entryPath.get()
        isPathValid, gamePath, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, pathGameGoodIcons = configureGamePath(pathToGame, pathAppdataStateRegionsOriginal, logger)

        clearExtendedGUI()    
        if isPathValid:
            with open(pathAppdataConfig, "w") as f:
                f.write("path=" + gamePath)

            app.focus_set()
            versions = getVersions(pathAppdataVersions, logger)
            imagePathIsCorrect = Image.open('resources/OK.png')
            app.btnPathIsCorrect.configure(image=ctk.CTkImage(imagePathIsCorrect))

            countStates, stateInfo, stateNameToID, stateIDToName = getStatesInfo(pathGameStateRegions, logger)
            app.resources = getResourcesFromConfig(countStates, logger)

            app.resources, stateInfo = getInfoFromStateRegions(pathGameStateRegions, stateInfo, app.resources, logger)
            app.resources = findStatesWithMostResources(app.resources, countStates)

            app.labelPresets = ctk.CTkLabel(master=app, text="Presets", justify=ctk.RIGHT)
            app.labelPresets.grid(row = 1, column = 0)

            app.comboBoxPresets = ctk.CTkComboBox(app, values=["Vanilla - No shuffle", "Gold", "Yellow & Black Gold", "Discoverables", "Mineable & Oil", "All but wood", "All"])
            app.comboBoxPresets.configure(command=functools.partial(switchResourcePresetCallback, resources=app.resources))
            app.comboBoxPresets.grid(row = 1, column = 1)

            app.labelHeaderResource = ctk.CTkLabel(master=app, text="Resource", justify=ctk.RIGHT)
            app.labelHeaderResource.grid(row = 2, column = 0)
            
            app.labelHeaderShuffle = ctk.CTkLabel(master=app, text="Shuffle?", justify=ctk.RIGHT)
            app.labelHeaderShuffle.grid(row = 2, column = 1)

            app.switchMaxResourcesStringVar = ctk.StringVar(value="0")
            app.switchMaxResources = ctk.CTkSwitch(master=app, text="Spoiler: Best states", variable=app.switchMaxResourcesStringVar, onvalue="1", offvalue="0",
                                                command=functools.partial(switchBestStatesCallback, app, stateIDToName, logger))
            app.switchMaxResources.grid(row = 2, column = 2)

            app.labelVersion = ctk.CTkLabel(master=app, text="Version", justify=ctk.RIGHT)
            app.labelVersion.grid(row = 1, column = 3)

            app.comboBoxVersions = ctk.CTkComboBox(app, values=versions, command=functools.partial(switchVersionCallback, app, pathAppdataVersions, pathGameStateRegions, logger))
            app.comboBoxVersions.grid(row = 1, column = 4)

            # app.imageRename = Image.open('resources/edit.png')
            # app.imagePathIsCorrect = Image.open('resources/OK.png')
            # app.btnRename = ctk.CTkButton(app, text = "", corner_radius=32, image=ctk.CTkImage(app.imageRename), fg_color="#dddddd",
            #                         command=None)
            # app.btnRename.grid(row=1, column=5)

            # app.imageDelete = Image.open('resources/delete.png')
            # app.btnDelete = ctk.CTkButton(app, text = "", corner_radius=32, image=ctk.CTkImage(app.imageDelete), fg_color="#dddddd",
            #                         command=None)
            # app.btnDelete.grid(row=2, column=5)

            app.imageOpen = Image.open('resources/open.png')
            app.btnOpen = ctk.CTkButton(app, text = "", corner_radius=32, image=ctk.CTkImage(app.imageOpen), fg_color="#dddddd",
                                    command=functools.partial(openFolderCallback(app, pathAppdataVersions)))
            app.btnOpen.grid(row=1, column=5)

            app.imagePathIsCorrect = Image.open('resources/OK.png')
            app.btnExecute = ctk.CTkButton(app, text = "Shuffle", corner_radius=32, 
                                    command=functools.partial(execute(app, versions, pathAppdataVersions, pathGameStateRegions, pathAppdataStateRegionsOriginal, pathGameHistoryBuildings, pathGameCompanies, logger)))
            app.btnExecute.grid(row=1, column=6)

            extendedGUIElements.extend([app.labelPresets, app.comboBoxPresets, app.labelHeaderResource, app.labelHeaderShuffle, app.switchMaxResources,
                                    app.labelVersion, app.comboBoxVersions, #app.btnRename, app.btnDelete, 
                                    app.btnExecute])
            for resKey, resource in app.resources.items():
                if resKey in IGNORED_RESOURCES:
                    continue
                resource['stringVar'] = ctk.StringVar(value="0")
                #imageRaw = Image.open(os.path.join(pathGameGoodIcons, resKey + ".dds"))
                #imageRaw = imageRaw.resize((15, 15))
                labelGoodName = ctk.CTkLabel(master=app, text=resKey.capitalize(), justify=ctk.RIGHT)
                                            #,image=ctk.CTkImage(imageRaw))
                labelGoodName.grid(row = TABLE_GOODS_FIRST_ROW + len(resourcesListGUI), column = 0)

                switchBox = ctk.CTkSwitch(master=app, text="", variable=resource['stringVar'], onvalue="1", offvalue="0",
                                                command=functools.partial(switchResourceCallback(resKey, app.resources, app.comboBoxPresets, logger)))
                
                if resource['strColor']:
                    switchBox.configure(progress_color="#" + resource['strColor'])
                else:
                    switchBox.configure(progress_color="#aaffaa")
                switchBox.grid(row = TABLE_GOODS_FIRST_ROW + len(resourcesListGUI), column = 1)

                resource['labelBestStates'] = ctk.StringVar(value=TEXT_DEFAULT_BEST_STATES)
                labelBestStates = ctk.CTkLabel(master=app, textvariable=resource['labelBestStates'], justify=ctk.LEFT)
                labelBestStates.grid(row = TABLE_GOODS_FIRST_ROW + len(resourcesListGUI), column = 2, columnspan = 2)

                resourcesListGUI.extend([labelGoodName, switchBox, labelBestStates])
        else:
            filePath = os.path.join('resources', 'wrong.png')
            if not os.path.exists(filePath):
                logger.error(f"No file at path {filePath}")
                sys.exit()
            app.imagePathIsCorrect = Image.open(filePath)
            app.btnPathIsCorrect.configure(image=ctk.CTkImage(app.imagePathIsCorrect))
    callback()
    return callback()   