# Moogles Intuition
#### A library to utilitize the data from XIVDataMining, TeamCraft, GarlandTools, Universalis and FF14Angler.

## Table of Contents

- [Installation](#installation)
- [Endpoints](#endpoints)
- [Usage](#usage)
- [Credits](#credits)
- [Issues]
- [Changelog]
- [Contributing](./CONTRIBUTING.md)


# Installation
Currently only available via `github`, eventually this will be available on `pypi.org`.
...

# Features
- Item lookup by Name or ID via `Moogle.get_item()`
    - Will return a best match/s. *See `limit_result` parameter.
    - Finds relative Item information such as Recipes, Fishing, SpearFishing, Gathering and Places.
- Getting bulk Universalis/Marketboard information for Items.
    - See `Moogle.get_current_marketboard_bulk()` and `Moogle.get_history_marketboard_bulk()`
- Provides suggested pricing for an Item. See `Moogle.get_suggested_price()`
    - Use current listings and recent history listings to give a "suggestive" price and stack size to sell the item.
- Currency Spending. See `Moogle.currency_spender()`
    - Returns a list of items with the highest sale velocity per World/Datacenter purchased with the specified currency.


# Usage

```py
from moogle_intuition import Moogle

moogle = Moogle().build()
#...
await moogle.clean_up()
```


...

# Credits
Universalis, GarlandToolsData, XIVDataMining and their XIVAPI Github Repo, TeamCraft, SquareEnix and en.ff14Angler.com
...


[Repo]: https://github.com/k8thekat/moogles_intiution/issues?q=is%3Aissue+is%3Aclosed
[Issues]: https://github.com/k8thekat/moogles_intiution/issues?q=is%3Aissue+is%3Aclosed
[Changelog]: ./CHANGELOG.md