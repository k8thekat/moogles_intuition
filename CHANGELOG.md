# Version - 1.0.0-dev - [67db0a1](https://github.com/k8thekat/moogles_intuition/commit/67db0a1)
## First stable Dev Release
- Updated documentation and added more modules to `__all__`.
- Relocated functionality regarding file handling into the `Builder` class.
- Relocated TeamCraft List generator to our base `Object` class.
- Fixed cache item logic in `Moogle.get_item()`
- Relocated functionality regarding `Recipe`, `Gathering` and `Fishing` to their respective classes.
- Relocated MakePlace related functionality to it's own structure.
- Updated naming conventions on marketboard functionality.
-- Fixed logic handling for bulk searching.
- Added `currency_spender` function to see what sells the "fastest" over currency price per unit.
- Fixed iteration logic bug in `Moogle.currency_spender()` function.
- Added more GarlandTools data handling to an `Item`.
- Added functionality to Iterate through `JobRecipe` recipes and `Recipes` ingredients and counts.
- Changed attributes referencing item ids to now resolve to actual `Item` objects, if applicable.
- Added `get_crafting_cost` for `Recipe` crafting vs purchasing.
- Fixed logic bug in fetching ff14 angler information for a `Fish` object.
- Added functionality to get  gathering node information related to a `Gathering` object from GarlandTools.
-- Added a `GatheringNode` class to handle the information.
- Updated `SuggestedPrice` functionality to support updated `UniversalisAPI` parameters.

### Fixed FF14 Angler lookups.
- Relocated functions related to an Item such as Gathering, Fishing and Recipes to the `Item` class.
- Updated docstrings for multiple class attributes.
- Sorted functions tied to `Builder` class.
- Added support for ignoring validation and rebuilding local data for our `Moogle` class via `Moogle.build` parameters.
- Finished docstring for `teamcraft_list` function.
- Added support for Garlandtools Data parsing for Gathering Nodes related to an `Item` class.
- Changed naming convetion of FF14angler class object integration in relation to an `Item` class along with attribute updates.

### Updated Item and Pyproject.toml
- Set `Item.description` default value to `None`.
- Updated pyproject.toml configs.

### Minor data change.
- Added `icon` attribute back to `Item` to make GarlandTools Icon data fetching simpler.
- `Item.get_icon` logic changed; no longer requires GarlandTools Data.
"
"# Updated Garlandtools data parsing.
- Removed logic to fetch data from `Item.get_vendors()` and `Item.get_tradeshops()`.


### Minor bug fixes and testing of Allagon Tools and GarlandTools API.
- Added Patch enum.
- Added Housing related enum values for `InventoryLocation`.
- Added test code to local.py for working on Allagon Tools and MakePlace.
- Updated TODO.md

## New! -> MakePlace Integration
- Added types for MakePlace JSON parsing.
- Added TeamCraft list generator.
- Added overloads for `Universalis` integration methods.
- Rebuilt the `currency_spender` function. (Still testing).
- Added a `universalis_url` property to the `Item` class object.
- Added `get_vendors` and `get_tradeshops` function for GarlandTools data.
- Added an `id` property to `JobRecipe`.
- Added `get_crafting_cost` function to `JobRecipe` and `Recipe`. See docstrings~
- Removed item lookup inside `Recipes` to prevent recursion bugs.
- Added comparison dunder methods to `InventoryItem`.

## ISSUES
- Fixed more `CachedSession` issues and un-initialized supporting classes. (GarlandTools, Universalis and Angler)
- Fixed logic bug in `get_item` resulting in returning `None`.
- Fixed logic issue with `get_current_marketboard` and `get_history_marketboard` not catching `Universalis` errors.
- Fixed cached session being closed early or not being used as the default session.
- Fixed typo in data structure checking for `_get_gathering_level`.

### Missing ff14angler data.
- Added a `MANIFEST.in` for ff14angeler data.
- Updated session handling for GarlandTools using CachedSessions.

### Updated gitHub actions.
- Forgot to update project_name and dir.

### Updated imports.
- Forgot to update package name.
- Added `async_universalis`.
- Failed `universalis` version resolution.
- Added get_icon for an `Item`.

## First beta-dev commit..
- Added github workflows and scripts.
- Added issue template.
- Added TODO and CHANGELOG info.
- Added VScode extension support.
- Added en.ff14angler response json structures for development.
- Added `local.py` for development.
- Re-organized repo and files.
- Split `GarlandToolsAPI` code into a separate library called `GarlandToolsAPI_wrapper`.
- Parsing of AllaganTools CSV data.
- Suggestive pricing for an Item based upon World/DC.
- Added Currency spender function to see fetch sellable items based upon a certain currency.
- Added Cheapest price searching for an item.

### v4.0.0 - Refactor
- Switched to new package manager. `uv`.
- Fixed typo's in Legal notices throughout library.
- Changed naming conventions of classes throughout library for clarity and simplicity.
- Added error/exception classes.
- Massive re-write on all classes, modules and functions. Simplified logic throughout.

### v`3.0.0`
- Relocated FF14Angler data structures to their own folder and files.
- Added support for Spearfishing and Spearfishing spots.
- Began adding functionality for FF14Angler website data parsing.
- Added a `sanitize_values` function to deal with entries of `place_name.json` having invalid strings in the name value.

### v`2.1.1` - FF14 Angler updates.
- Added docstrings to the `bs4` Soup class overwrites to help with typing.
- Changed the inheritance of `CustomTag` to `bs4.Tag` and redefined the `.find()` function separately.

### v2.1.0
- Implemented `bs4` parsing of FF14Angler website to fetch specific fishing location information.
- New type `FishDataTyped` to handle the return of `FFXIVHandler.get_fish_data()`.

### v2.0.0
- Forgot the `__init__.py` - oops~

### v2.0.0
- Updated `__all__` for `_enums.py` to include the upcoming FishingSpot information.
-- Added additional values to `InventoryLocationEnum` to handle Allagon Tools CSV data.
-- Added a `FishingSpotCategoryEnum` to handle the "type" of fishing action needed to catch said fish.
- New entries for `_types.py` to handle AllagonTools, FF14Angler and `FFXIVHandler.get_item()` parameters.
- `FFXIVObject` implementation to house base functionality and redue redundant code.
- `FFXIVInventoryItem` class to handle Allagon Tools CSV parsing was made.
- Updated type definition for multiple ClassVars.
- Added support for Universalis on an `FFXIVItem` and added a bulk marketboard search to `FFXIVHandler`.
-- Added a mutl_field attribute to Universalis for trimming API fields.
-- Added a new type for handling bulk marketboard search results data.
- Added `FFXIVHandler.parse_atools_csv` to handle an Allagon Tools CSV file.

Co-authored-by: Lightning <LightningTH@users.noreply.github.com>

### v.1.1.0 - Marketboard Support
- Relocated `Universalis` related TypedDicts to their respective file inside the `universalis/` dir.
- Removed un-needed attributes from `FFXIVHandler` related to CSV data.
- Updated types of multiple function parameters.
- Removed `overloads` for `FFXIVHandler.get_item()` until I understand them better.
- Finished remaining docstring TODOs for `FFXIVHandler`.
- Added function `FFXIVHandler.get_mb_current_data()`  to retrieve Universalis marketboard data which supports lists of entries either by name or ids.
- Added funciton `FFXIVItem.mb_current_data()` to retrieve Universalis marketboard data for the related item.
- Added `logger.debug` logic to `UniversalisAPI.get_current_data()`.
- Updated types for class `universalis.CurrentData` and `universalis.CurrentKeys`.

### v1.0.0
- Rebuilt structure of `FFXIVHandler` to validate files on init. Will fetch relevant data if required.
- Added `FFXIVHandler.build_handler()` function to build required data for operation.
- Seperated GarlandTools and Universalis into their own directories to better facilitate file structure via imports.

- Updated TODO and .gitingore.


# Version - 0.0.0 [000000]
- Initial build of the project.
...