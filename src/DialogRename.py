import functools
import customtkinter as ctk

from callbacks import submit_rename

class RenameDialog(ctk.CTkToplevel):
    def __init__(self, name, app, pathAppdataVersions, pathGameStateRegions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("400x300")

        self.label = ctk.CTkLabel(self, text="New name:")
        self.label.grid(row=0, column=0, padx=(10, 5), pady=10)

        self.entry = ctk.CTkEntry(self, width = 300)
        self.entry.insert(0, name)
        self.entry.grid(row=1, column=0, padx=(10, 5), pady=10)
        

        self.btnRename = ctk.CTkButton(self, text = "Confirm",
                                 command=functools.partial(submit_rename, self, app, pathAppdataVersions, pathGameStateRegions))
        self.btnRename.grid(row=2, column=0, padx=(10, 5), pady=10)