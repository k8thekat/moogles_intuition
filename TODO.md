# Scope:
The overarching generalization of what I want `Moogle Intuition` to accomplish.

## Handle CSV data on creation and build all JSON files similar to local.py
    - *DONE* - Build class/function to get or handle the data. (FFXIVHandler)
    - *DONE*- Function to validate JSON or CSV files if not use `asyncio.create_task()` and go retrieve the data.
    - *DONE* - Finish dynamic function to fetch CSV data.
    - *DONE* - Change file names to match URL dict structure for clarity.
    - *DONE* - Add logic for when `.json` file doesn't exist to get data and rebuild as needed.
    - *Done* - Fix functions for building Enums/etc inside FFXIVHandler - See FFXIVBuilder.

## Full Item lookup by ID or Name: 
    - *DONE* Supports partial string matching via Fuzz. 
    - *DONE* Recipe Info
    - How to know if an Item can be Fished or Gathered?
        - *DONE* - Fishing
        - *DONE* - Gatherable


## Features:
Additional features and or integration with other platforms.

### Marketboard/Universalis Interaction:
    - *DONE* - FFXIVItem - Fetch current Marketboard Information.
    - *DONE* - FFXIVHandler - Bulk item fetching of current Marketboard Information.
    - Query Builder class to handle trimming fields.
        - *DONE* - Use properties as a place holder.
    - Current Data/History Data class
        - Get most common stack histogram? HQ/NQ
            - Format the floats?
        - *DONE* -  Convert `last_upload_time` into a datetime object. (It's a timestamp)

### FF14Angler Integration/Links - Jewell is parsing the HTML
    - *DONE* - ? Possibly turn this into it's own submodule similar to `Universalis`.
    - Consider storing fetched data in an array attached to `FFXIVHandler` to prevent multiple web requests.
        - *DONE* - Storing `location_name/place_name : location/spot_id`. See -> <FFXIVBuilder.build()> -> <FFXIVHandler.get_location_id_mapping()>
        - *DONE* - Storing `fish_name: fish_id`. See -> <FFXIVBuilder.build() -> <FFXIVHandler.get_fish_id_mapping()>
    - *DONE* - Links -> https://en.ff14angler.com/
    - FF14Fish
        - *DONE* - Add a `Optimal Bait/hook_percent function. See `<AnglerFish.best_bait()>`
    
    - Fetching Location ID information.
        - *DONE* - Functions to fetch data and parse html.
        - *DONE* - Get Lure to Fish % chance.
            - *DONE* - Proper handling of errors and validate operations of functions for data.
            - *DONE* - Need to Sanitize `location_id` mapping function; remove/replace improper characters. "The <Emphasis>Adventure</Emphasis>"
        - *DONE* -  Need to setup attributes for `FFXIVHandler` and attaching to the `FFXIVItem` or `FFXIVFishParameter` class.
    - Fetching Fish ID
        - *DONE* - Create FF14 Fish Name -> ID Map
        - *DONE* - Get fishing location information by FF14 Fish ID.

### Garland Tools:
    - Garland Tools API Wrapper Integration -
    -  *DONE*  Link -> https://www.garlandtools.org/db/#item/[X] - X = `item_id`

### FFXIV Console Games Wiki 
    - *DONE* - Link -> https://ffxiv.consolegameswiki.com/wiki/FF14_Wiki


## Current Objects:
The current data structions/class's used to implement the *Scope*.
- *DONE* - Remove un-used attributes from classes to prevent bloat.



### FFXIVFishingSpot
    Create lookup function/reference for FF14Angler Integration
        - *Done* - Support spearfishing


### FFXIVInventoryItem
    Parse Allagon Tools csv file into an object.
    - *DONE* - Loading and Converting of Allagaon Tools CSV data into Item Objects.
    - *DONE* - Prep for Universalis interaction.
    - TODO - Searching up a Recipe and see it's cost vs making it.
        - Sort by least missing ingredients.
        - Attach Costs to items and or cheapest to "craft".


### Teamcraft Integration
    - Take an item and generate a Teamcraft list?

### MakePlace Integration
    - Add support for Seeing if an item can be purchased or not.
    - Add Color code conversion to Ingame Dye
    - Support getting the count of "material" for crafting.
    - {
			"itemId": 21109,
			"name": "Blank Hingan Partition",
			"transform":
			{
				"location": [ 993.64805000000001, 617.84142999999995, -699.99979999999994 ],
				"rotation": [ 0, -0, 0.70710673118654366, 0.70710683118654805 ],
				"scale": [ 1, 1, 1 ]
			},
			"properties":
			{
				"material":
				{
					"name": "Alpine Inner Wall",
					"itemId": 14070
				}
			}
		},
