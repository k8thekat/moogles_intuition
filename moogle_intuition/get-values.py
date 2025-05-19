import csv
import datetime
import json
import math
import os
import sys
import time

import requests

ItemsToPrice = """Magic Broom
Summoning Bell
Woodworking Bench
Goldsmithing Bench
Leatherworking Bench
Clothcraft Loom
Regal Letter Box
Alps Striking Dummy
Glade Path Light
Longcase Chronometer
Oriental Altar
Oriental Striking Dummy
Kimono Hanger
Far Eastern Gazebo
Royal Bed
Drachen Armor Augmentation
Choral Attire Augmentation
Healer's Attire Augmentation
Inferno Bow
Inferno Cane
Beak of the Vortex
Spine of the Vortex
Mischievous Moggle Mogbow
Maleficent Moggle Mogstaff
Artisan's Grinding Wheel
Artisan's Spinning Wheel
Wootz Knuckles
Staggered Shelf
Oriental Wood Bridge
Oriental Deck
Paladin's Mighty Levin Arms
Mighty Thunderstorm
Mighty Thunderbolt
Mighty Thunderdart
Mighty Thundersparks
Mighty Thunderclap
Mighty Thundershower
High Adjudicator's Gavel
High Adjudicator's Staff
Ona Ramuhda First Edition
The Law of Levin First Edition
Heavy Metal Claws
Heavy Metal Greatsword
Heavy Metal Culverin
Odyssey Miniature
Grade 3 Picture Frame
Mighty Thunderstroke
Glade Bachelor's Chest
Portable Stepladder
Glade Partition Door
Oasis Partition Door
Level 2 Aetherial Wheel Stand
Enterprise-type Hull
Odyssey-type Hull
Tatanora-type Hull
Invincible II-type Propellers
Odyssey-type Bladders
Invincible-type Forecastle
Invincible-type Aftcastle
Shark-class Stern
Shark-class Bow
Unkiu-class Pressure Hull
Whale-class Stern"""

last_api_call = datetime.datetime.now()
max_apis_sec = 10


def CallAPI(api):
    global last_api_call
    while 1:
        try:
            now_time = datetime.datetime.now()
            max_diff = datetime.timedelta(milliseconds=1000 / max_apis_sec)
            if (now_time - last_api_call) < max_diff:
                sleep_time = (max_diff - (now_time - last_api_call)).total_seconds() + 0.1
                time.sleep(sleep_time)

            r = requests.get(api)
            if r.status_code != 200:
                time.sleep(1)
                continue

            data = r.json()
            last_api_call = datetime.datetime.now()
            return data
        except Exception as ex:
            print(ex, r.status_code)


def GetPrices(items):
    final_data = {}

    for i in range(0, len(items), 100):
        # 100 items at a time to the API
        item_list = []
        for x in range(0, 100):
            if i + x >= len(items):
                break
            item_list.append(ItemNames[items[i + x]])

        # get the items
        json_data = CallAPI("https://universalis.app/api/v2/aggregated/Crystal/" + ",".join(item_list))
        json_data = json_data["results"]
        for entry in json_data:
            final_data[ItemIDs[str(entry["itemId"])]["en"]] = {"price": entry, "history": None}

        # get the history for the items
        json_data = CallAPI("https://universalis.app/api/v2/history/Crystal/" + ",".join(item_list))
        json_data = json_data["items"]
        for entry in json_data:
            final_data[ItemIDs[str(entry)]["en"]]["history"] = json_data[entry]
            while len(final_data[ItemIDs[str(entry)]["en"]]["history"]["entries"]) and (
                final_data[ItemIDs[str(entry)]["en"]]["history"]["entries"][0]["pricePerUnit"] > 1000000
            ):
                final_data[ItemIDs[str(entry)]["en"]]["history"]["entries"].pop(0)

    return final_data


def GetItemIDs():
    f = open("items.json", encoding="utf-8")
    data = json.load(f)
    f.close()
    return data


def GetWorlds():
    f = open("World.csv", encoding="utf-8")
    data = f.readline()
    data = csv.DictReader(f)
    out_data = {}
    for entry in data:
        if len(entry["Name"]) == 0:
            continue
        out_data[entry["#"]] = entry["Name"]
    f.close()
    out_data.pop("int32")
    return out_data


def GetWorldDC():
    f = open("WorldDCGroupType.csv", encoding="utf-8")
    data = f.readline()
    data = csv.DictReader(f)
    out_data = {}
    for entry in data:
        if len(entry["Name"]) == 0:
            continue
        out_data[entry["#"]] = entry["Name"]
    f.close()
    return out_data


def GenerateItemNameToID(items):
    out_items = {}
    for entry in items:
        out_items[items[entry]["en"]] = entry
    return out_items


def GenerateWorldNameToID(worlds):
    out_worlds = {}
    for entry in worlds:
        out_worlds[worlds[entry]] = entry
    return out_worlds


def ImportCurrentItems(csv_file, MatchSource=None, MatchSection=None):
    Items = {}

    # item locations to skip
    SkipList = ["Armory", "Currency", "Glamour Chest", "Market", "Equipped Gear", "Crystals"]

    f = open(csv_file)
    data = csv.DictReader(f)
    for entry in data:
        # if GC then skip it
        if entry["Inventory Location"].startswith("Free Company"):  # and (not entry["Inventory Location"].startswith("Free Company Chest - 5")):
            continue

        Skipped = False
        for skip_entry in SkipList:
            if entry["Inventory Location"].startswith(skip_entry):
                Skipped = True
                break
        if Skipped:
            continue

        # if we have a source to match and it doesn't match then ignore
        if (MatchSource and entry["Source"] != MatchSource) or (MatchSection and (not entry["Inventory Location"].startswith(MatchSection))):
            continue

        if entry["Type"] not in ["HQ", "NQ"]:
            continue

        # get the item counts
        if entry["Name"] not in Items:
            Items[entry["Name"]] = {"NQCount": 0, "HQCount": 0}
        Items[entry["Name"]][entry["Type"] + "Count"] += int(entry["Total Quantity Available"])
    f.close()
    return Items


def FakeItems(ItemList):
    # take a list of items and fake a bunch of entries so we can get prices for a single of it
    ItemNames = ItemList.split("\n")

    CurrentItems = {}
    for entry in ItemNames:
        CurrentItems[entry] = {"NQCount": 1, "HQCount": 0}
    return CurrentItems


os.chdir(os.path.dirname(sys.argv[0]))

ItemIDs = GetItemIDs()
ItemNames = GenerateItemNameToID(ItemIDs)
WorldIDs = GetWorlds()
WorldNames = GenerateWorldNameToID(WorldIDs)
WorldDC = GetWorldDC()

# CurrentItems = ImportCurrentItems("../sekushina.csv")
# CurrentItems = ImportCurrentItems("../shea-rabbit bag 5.csv")
CurrentItems = FakeItems(ItemsToPrice)

ItemList = []
for entry in CurrentItems:
    if "Materia" in entry:
        ItemList.append(entry)
ItemList = list(CurrentItems.keys())
Prices = GetPrices(ItemList)
open("prices.json", "w").write(json.dumps(Prices))
# Prices = json.loads(open("prices.json","r").read())

total_low = 0
total_high = 0
counts = 0
calc_data = []
for entry in Prices:
    try:
        low_price = Prices[entry]["price"]["nq"]["minListing"]["dc"]["price"]
        last_sale_price = Prices[entry]["price"]["nq"]["recentPurchase"]["dc"]["price"]
        hours_ago = (
            datetime.datetime.now() - datetime.datetime.fromtimestamp(Prices[entry]["price"]["nq"]["recentPurchase"]["dc"]["timestamp"] / 1000)
        ).total_seconds()
        hours_ago = math.floor(hours_ago / 60 / 60)
        item_count = CurrentItems[entry]["NQCount"] + CurrentItems[entry]["HQCount"]
        profit_low = low_price * item_count
        profit_high = last_sale_price * item_count
        calc_data.append({
            "name": entry,
            "item_count": item_count,
            "low_price": low_price,
            "last_sale_price": last_sale_price,
            "hours_ago": hours_ago,
            "profit_low": profit_low,
            "profit_high": profit_high,
        })
        # print(f"{entry} ({item_count}): Lowest Price {low_price}, Last Sale: {last_sale_price} {hours_ago} hours ago - potential {profit_low} to {profit_high} profit")
        total_low += profit_low
        total_high += profit_high
        counts += item_count
    except Exception:
        import traceback

        traceback.print_exc()
        import pprint

        pprint.pprint(Prices[entry])
        sys.exit(0)

calc_data.sort(key=lambda cd: cd["low_price"], reverse=False)
for entry in calc_data:
    print(
        f"{entry['name']} ({entry['item_count']}): Lowest Price {entry['low_price']}, Last Sale: {entry['last_sale_price']:,} {entry['hours_ago']} hours ago - potential {entry['profit_low']} to {entry['profit_high']} profit"
    )

print(f"Total Profit: {total_low} to {total_high}")
print(f"Total counts: {counts}")
