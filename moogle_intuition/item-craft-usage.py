import csv
import json
import os
import sys

from garlandtools import GarlandTools

api = GarlandTools()


def get_data(item):
    return json.loads(api.item(item).content)


def GetFinalItems(item_id):
    cryptomeria_lumber = get_data(item_id)
    final_build_items = dict(cryptomeria_lumber["item"]["ingredient_of"])

    # original dicts list a count of the lumber, put it into a count field then add the name
    for entry in final_build_items:
        count = final_build_items[entry]
        final_build_items[entry] = {"Count": count}
        for p in cryptomeria_lumber["partials"]:
            if p["id"] == entry:
                final_build_items[entry]["Name"] = p["obj"]["n"]
                break

    # go through each item and grab what items require it
    for entry in final_build_items:
        final_build_items[entry]["data"] = get_data(entry)

    return final_build_items


def ImportCurrentCounts(name, csv_file):
    # item locations to skip
    SkipList = ["Armory", "Currency", "Glamour Chest", "Market", "Equipped Gear", "Crystals"]

    f = open(csv_file)
    Items = {}
    data = csv.DictReader(f)
    for entry in data:
        # if GC then skip it
        if entry["Inventory Location"].startswith("Free Company"):  # and (not entry["Inventory Location"].startswith("Free Company Chest - 5")):
            continue

        # if it starts with any of the items from skip list then skip it
        Skip = False
        for skip_entry in SkipList:
            if entry["Inventory Location"].startswith(skip_entry):
                Skip = True
                break
        if Skip:
            continue

        # combine NQ and HQ items
        if entry["Name"] not in Items:
            Items[entry["Name"]] = {"Count": 0, "Location": []}
        Items[entry["Name"]]["Count"] += int(entry["Total Quantity Available"])
        if name not in Items[entry["Name"]]["Location"]:
            Items[entry["Name"]]["Location"].append(name)
    f.close()
    return Items


def CopyCounts(Counts):
    NewCounts = dict(Counts)
    for entry in NewCounts:
        NewCounts[entry] = dict(NewCounts[entry])
    return NewCounts


def GetPercentCounts(Ingredients, IngredientNames, CurrentCounts):
    # go through the item list and count how much of it we have then
    # print the data and a percentage for it
    TotalCount = 0
    ActualCount = 0
    ItemCounts = CopyCounts(CurrentCounts)
    PercentData = {}
    Ingredients = list(Ingredients)
    for Entry in Ingredients:
        Count = Entry["amount"]
        TotalCount += Count
        for nentry in IngredientNames:
            if nentry["id"] == Entry["id"]:
                name = nentry["name"]
                break
        Entry["Name"] = name

        # deduct from the item count
        if name in ItemCounts:
            if ItemCounts[name]["Count"] < Count:
                Count = ItemCounts[name]["Count"]
            ItemCounts[name]["Count"] -= Count
        else:
            Count = 0
        Entry["HaveCount"] = Count
        ActualCount += Count

    # each of these require a frame, grab the frame and process it too
    FrameID = Ingredients[0]["id"]
    SubFrameID = -1
    for Entry in IngredientNames:
        if Entry["id"] == FrameID and Entry["name"].endswith(" Frame"):
            SubFrameID = Entry["tradeShops"][0]["listings"][0]["currency"][0]["id"]

            # go find out what the sub frame requires
            SubFrameData = get_data(SubFrameID)
            SubFramePercent, SubIngredients, ItemCounts = GetPercentCounts(
                SubFrameData["item"]["craft"][0]["ingredients"], SubFrameData["ingredients"], ItemCounts
            )

            # now combine it with our data
            TotalCount += SubFramePercent["TotalCount"]
            ActualCount += SubFramePercent["ActualCount"]
            Ingredients += SubIngredients
            break

    return {"TotalCount": TotalCount, "ActualCount": ActualCount, "Complete": ActualCount / TotalCount}, Ingredients, ItemCounts


def PrintPercentCounts(TopName, PercentData, Ingredients, Prices):
    if TopName in Prices:
        if "dc" not in Prices[TopName]["price"]["nq"]["minListing"]:
            LastPrice = -1
        else:
            LastPrice = Prices[TopName]["price"]["nq"]["minListing"]["dc"]["price"]
    else:
        LastPrice = -1
    print(f"{TopName} - {PercentData['ActualCount'] / PercentData['TotalCount'] * 100:0.2f}% - {LastPrice:,} gil")
    for Entry in Ingredients:
        if Entry["HaveCount"] != Entry["amount"]:
            print(f"\t{Entry['Name']}: {Entry['HaveCount']}/{Entry['amount']}")


def ImportTeamCraftList(craft_file):
    data = open(craft_file).read().split("\n")

    Items = {}
    for entry in data:
        # skip blank lines and section headers
        if len(entry) == 0 or entry.endswith(":"):
            continue

        cur_entry = entry.split()
        item_name = " ".join(cur_entry[1:])
        item_count = int(cur_entry[0][:-1])
        if item_name not in Items:
            Items[item_name] = 0
        Items[item_name] += item_count

    return Items


AllItems = GetItemIDs()
AllItemNames = GenerateItemNameToID(AllItems)
CurrentCounts = ImportCurrentCounts("Sekushina", "sekushina.csv")
# ClaimedItems = ImportTeamCraftList("claimed-sekushina.txt")
# for entry in ClaimedItems:
#    CurrentCounts[entry]["Count"] -= ClaimedItems[entry]
FinalItems = GetFinalItems(AllItemNames["Ancient Lumber"])

# get final counts of things
for ItemID, CurItem in FinalItems.items():
    CurItem["Percentage"], CurItem["Ingredients"], CurItem["ItemsLeft"] = GetPercentCounts(
        CurItem["data"]["item"]["craft"][0]["ingredients"], CurItem["data"]["ingredients"], CurrentCounts
    )

PercentList = []
for ItemID, CurItem in FinalItems.items():
    PercentList.append([ItemID, CurItem["Percentage"]["Complete"]])

Prices = json.loads(open("inventory-value/prices.json").read())

PercentList.sort(key=lambda a: a[1], reverse=True)
for ItemID, ItemPercent in PercentList:
    if ItemPercent < 0.2:
        break

    PrintPercentCounts(FinalItems[ItemID]["Name"], FinalItems[ItemID]["Percentage"], FinalItems[ItemID]["Ingredients"], Prices)

"""
print("Missing prices:")
for ItemID in FinalItems:
    print(FinalItems[ItemID]["Name"])
"""
