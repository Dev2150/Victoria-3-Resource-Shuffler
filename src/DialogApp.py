import functools
import customtkinter as ctk
from PIL import Image
import re
from callbacks import switch_resource_callback, switch_resource_preset_callback
from globalProperties import resourcesToIgnore, resourcesListGUI
from services import configureGamePath, execute, getResourcesFromConfig, getStatesInfo, getVersions

class App(ctk.CTk):
    def __init__(self, pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 5
        
        self.title("Victoria 3 Resource Shuffler")
        self.geometry("1000x400")
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

def updateBasedOnEntryPath(app, pathAppdataConfig, pathAppdataStateRegionsOriginal, logger, pathAppdataVersions, event):
    def callback():
        pathToGame = app.entryPath.get()
        isPathValid, gamePath, pathGameStateRegions, pathGameHistoryBuildings, pathGameCompanies, pathGameGoodIcons = configureGamePath(pathToGame, pathAppdataStateRegionsOriginal, logger)
        
        global resourcesListGUI
        for widget in resourcesListGUI:
            widget.destroy()
        resourcesListGUI = []
        if isPathValid:
            with open(pathAppdataConfig, "w") as f:
                f.write("path=" + gamePath)

            versions = getVersions(pathAppdataVersions, logger)
            imagePathIsCorrect = Image.open('resources/OK.png')
            app.btnPathIsCorrect.configure(image=ctk.CTkImage(imagePathIsCorrect))

            countStates, stateInfo, stateNameToID, stateIDToName = getStatesInfo(pathGameStateRegions, logger)
            app.resources = getResourcesFromConfig(countStates, logger)

            app.labelPresets = ctk.CTkLabel(master=app, text="Presets", justify=ctk.RIGHT)
            app.labelPresets.grid(row = 1, column = 0)

            app.comboBoxPresets = ctk.CTkComboBox(app, values=["Vanilla - No shuffle", "Gold", "Yellow & Black Gold", "Discoverables", "Mineable & Oil", "All but wood", "All"])
            app.comboBoxPresets.configure(command=functools.partial(switch_resource_preset_callback, resources=app.resources))
            app.comboBoxPresets.grid(row = 1, column = 1)

            app.labelHeaderResource = ctk.CTkLabel(master=app, text="Resource", justify=ctk.RIGHT)
            app.labelHeaderResource.grid(row = 2, column = 0)
            
            app.labelHeaderShuffle = ctk.CTkLabel(master=app, text="Shuffle?", justify=ctk.RIGHT)
            app.labelHeaderShuffle.grid(row = 2, column = 1)

            app.labelVersion = ctk.CTkLabel(master=app, text="Version", justify=ctk.RIGHT)
            app.labelVersion.grid(row = 1, column = 3)

            app.comboBoxVersions = ctk.CTkComboBox(app, values=versions, command=None)
            app.comboBoxVersions.grid(row = 1, column = 4)

            app.imageRename = Image.open('resources/edit.png')
            app.imagePathIsCorrect = Image.open('resources/OK.png')
            app.btnRename = ctk.CTkButton(app, text = "", corner_radius=32, image=ctk.CTkImage(app.imageRename), fg_color="#dddddd",
                                    command=None)
            app.btnRename.grid(row=2, column=3)

            app.imageDelete = Image.open('resources/delete.png')
            app.btnDelete = ctk.CTkButton(app, text = "", corner_radius=32, image=ctk.CTkImage(app.imageDelete), fg_color="#dddddd",
                                    command=None)
            app.btnDelete.grid(row=2, column=4)

            app.imagePathIsCorrect = Image.open('resources/OK.png')
            app.btnExecute = ctk.CTkButton(app, text = "Shuffle", corner_radius=32, 
                                    command=functools.partial(execute(app, versions, pathAppdataVersions, pathGameStateRegions, pathAppdataStateRegionsOriginal, pathGameHistoryBuildings, pathGameCompanies, logger)))
            app.btnExecute.grid(row=1, column=6)

            resourcesListGUI.extend([app.labelPresets, app.comboBoxPresets, app.labelHeaderResource, app.labelHeaderShuffle, 
                                    app.labelVersion, app.comboBoxVersions, app.btnRename, app.btnDelete, app.btnExecute])
            for resKey, resource in app.resources.items():
                if resKey in resourcesToIgnore:
                    continue
                resource['stringVar'] = ctk.StringVar(value="0")
                #imageRaw = Image.open(os.path.join(pathGameGoodIcons, resKey + ".dds"))
                #imageRaw = imageRaw.resize((15, 15))
                label = ctk.CTkLabel(master=app, text=resKey.capitalize(), justify=ctk.RIGHT)
                                            #,image=ctk.CTkImage(imageRaw))
                label.grid(row = 3 + len(resourcesListGUI), column = 0)

                switchBox = ctk.CTkSwitch(master=app, text="", variable=resource['stringVar'], onvalue="1", offvalue="0",
                                                command=functools.partial(switch_resource_callback(resKey, app.resources, app.comboBoxPresets, logger)))
                if resource['strColor']:
                    switchBox.configure(progress_color="#" + resource['strColor'])
                else:
                    switchBox.configure(progress_color="#aaffaa")
                switchBox.grid(row = 3 + len(resourcesListGUI), column = 1)
                resourcesListGUI.extend([label, switchBox])
        else:
            app.imagePathIsCorrect = Image.open('resources/wrong.png')
            app.btnPathIsCorrect.configure(image=ctk.CTkImage(imagePathIsCorrect))
    callback()
    return callback()