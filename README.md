# Most followed Instagram accounts: daily follower counts

Public follower counts of the most-followed Instagram accounts, one row per account per reading. This is the data behind [FastSocial Top Charts](https://fastsocial.co/most-followed-instagram-accounts) and [Instagram Statistics](https://fastsocial.co/instagram-stats). It updates every day.

## Files

| File | Contents |
|---|---|
| `data/daily.csv` | Every reading since 25 Sep 2026 |
| `data/latest.csv` | Newest reading per account, ordered by rank |
| `data/monthly/YYYY-MM.csv` | Readings for one month |
| `data/manifest.json` | Row count, account count, first and last date |

## Columns

| Column | Meaning |
|---|---|
| `date` | Day of the reading (UTC), YYYY-MM-DD |
| `username` | Instagram username, without the @ |
| `followers` | Public follower count shown on the profile that day |
| `name` | Display name |
| `category` | Main category: Sports, Music, Film & TV, Creators, Fashion & beauty, Brands, Media, Public figures, or blank |
| `country` | Two-letter country code (ISO 3166-1), blank when unknown |
| `type` | `person` or `org` |
| `rank` | Rank by followers at the latest reading, among the accounts tracked (same as Top Charts) |
| `also_in` | Other categories the account belongs to, separated by `; `. Blank for most accounts |

## Method

- Counts are the public follower numbers shown on each profile. They are not estimated or adjusted.
- The top 500 accounts are read every day. The rest are read every five days, so not every account has a row for every date.
- Candidate accounts come from Wikidata entries that list an Instagram username, plus a short hand-kept list.
- Private accounts are left out. Accounts can ask to be removed through the [opt-out form](https://fastsocial.co/most-followed-instagram-accounts#opt-out). Removed accounts are taken out of the whole history.
- `rank` is the current rank, not the rank on the day of the reading.

Full method: https://fastsocial.co/instagram-stats#data

## Licence and credit

[CC BY 4.0](LICENSE). Free to use, share and adapt, including commercially. Credit "FastSocial" and link to the source, for example:

> Data: [FastSocial Top Charts](https://fastsocial.co/most-followed-instagram-accounts), CC BY 4.0

## Also available

- Direct download: https://fastsocial.co/instagram-stats/data/daily.csv.gz
- JSON of the current chart: https://fastsocial.co/static/mf/top.json
- API: https://fastsocial.co/instagram-api
