# TODO
The current issues and TODOs for `Moogle Intuition`.

# Move functions to their related classes - 10/21
- Relocate funcs such as `_get_fishing_spot`, `_get_spearfishing_spot`, ...
- Possibly relocate `_reference_dict` and `_load_json` to the `Builder` class?

# Clean up Currency Spender func - 10/17


## Features:
Additional features and or integration with other platforms.
- See about checking the gitHub for a release for XIV_Datamining files.

### FFXIVInventoryItem
    Parse Allagon Tools csv file into an object.
    - *DONE* - Loading and Converting of Allagaon Tools CSV data into Item Objects.
    - *DONE* - Prep for Universalis interaction.
    - Searching up a Recipe and see it's cost vs making it.
        - Sort by least missing ingredients.
        - Attach Costs to items and or cheapest to "craft".


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
