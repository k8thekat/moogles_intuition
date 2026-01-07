# TODO
The current issues and TODOs for `Moogle Intuition`.
- Setup pypi/etc
- Double check docstrings and names.
- Perform a Unit Test.
- See about checking the gitHub for a release for XIV_Datamining files.

## Features:
Additional features and or integration with other platforms.

- Support Company/FC Workshop Items?
-- CompanyCraftSequence.csv has part fields -> CompanyCraftPart.csv has process fields -> CompanyCraftProcess.csv that has the actual item and quantity values


## MakePlace
- If the item is a raw ingredient; we should deduct the ingredients from the wanted Items.
- Add function to take an `Inventory` from say AllaganTools or similar; and deduct the `Items` recipe cost from that supplied Inventory.
    - Return updated `Inventory` and also return a needed/remaining `Inventory` along with a deducted `Inventory` count.


## GarlandTools Parsing
- Support `Item` -> Instance parsing (where to get/etc)
- Support `Item` -> Quest info
- Support `Item` -> Vendor Info