# Victoria 3 Resource Shuffler

![](https://i.imgur.com/jZFoA0N.png)

### What?
**Application** (**not** **mod**) that **permutates** the **resources** in the world
### How?
* Parses the game's files so that it extracts each states' resources, including the discoverables
* It also extracts information about initial  buildings and companies
* **It shuffles the resources you specify**

### Why?
* I do not like this side of meta where you secure certain states for the long-term economy of your nation. 
* (i.e. I do not like securing for gold states like Vrystaat, the nation of Peru or Borneo)
* The AI is dumb, it does not learn from plays, about best places to expand to, unlike players. Nor it reads the game's files

## ...Why?
###Because it's FUN:
* Make new strategies every play
* Seek the moved resources
* Pay attention to notifications of discoveries of gold, oil and rubber
* Might make you wage war over another countries
* A more interesting diplomacy emerges

### Who for?
Intermediate/Pro players

## Snapshot of the application

![](https://i.imgur.com/5vDwlID.png)

# Features
* Makes a **back-up**
* You can **choose** precisely the set of **resources** to be **shuffled**
* Or you can select a certain **preset**, e.g. only shuffle gold, only shuffle gold & oil, only shuffle the discoverable resources, etc.
* If you choose to shuffle resources like iron, lead, sulfur, then expect new emergences of **MAPI combos**
* **Buildings in 1836 are protected** - there are guaranteed specific resources for every state, so that the initial buildings work (as opposed to there being no resource thus the buildings vanish)
* **Companies** *that require certain states* are **protected** - you'll still be able to found them
* Can show the **top 5 states** for each resource (includes discoverables) - you have to enable the "Spoiler: Best states" switch
* The app remembers the versions of the  worlds you generate
* You can easily **go back** to play **the original game** or **previous new worlds**
* When you have selected a version - you're done and you can close the app - the game is loaded with the corresponding set of resources

# How to use?
* Prevent the anti-virus from interfering with the executable file. I've seen online that python executables are prone to be considered viruses. Yes, what your anti-virus thinks is fake news.
* **Provide the path to the Victoria 3 folder**. **It must contain the folders bin, game, launcher**; (You will only have to do this once, since the path is persistent)
* If the path is corect, then you will see a **green tick icon** and you will unlock the rest of the interface. (The app will start unlocked from now on)
* If you **want to generate a new world**:
* 1) on the left side, either select a certain preset OR you can be picky about the resources you want to shuffle; 
* 2) Click  the '**Shuffle**' button. If you want, you can rename the new world version. You're ready to play
* If you **want to go back to a world**, then select it from the version dropdown box - and that's it, you can close the app and play the game

### You can play multiplayer:
* In the app you can press the button which opens the folder for the version, and put it inside a mod folder, with the path `game\map_data\state_regions`

### If you provide a path to a mod instead, that contains:
* game\map_data\state_regions
* game\common\history\buildings
* game\common\company_types

* and configure resources.ini

* Then you can **add new permutable resources**, e.g. uranium;

### Initial motivation
* https://www.reddit.com/r/victoria3/comments/1bs0z48/825_hours_in_and_i_just_learned_how_insane_the/?ref=share&ref_source=link
* https://www.reddit.com/r/victoria3/comments/1bsmizw/mod_for_random_gold_oil_spawn/?ref=share&ref_source=link
* Seeing pro players go for the same set of states

### Ways the application can improve:
* **Shuffle agricultural goods** (while also, of course, protecting initial buildings & companies)
* **Protect all companies**: For every company that requires a set of resources in a certain region, give a random region's state the set of resources
* Dynamically **show good icons** next to each name (tried, but loading .dds files makes it boot very slowly)