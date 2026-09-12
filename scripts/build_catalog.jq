def pad2: tostring | if length < 2 then "0" + . else . end;
def clean_summary:
  (. // "")
  | gsub("<[^>]+>"; "")
  | gsub("&amp;"; "&")
  | gsub("&quot;"; "\"")
  | gsub("&#39;"; "'")
  | gsub("&apos;"; "'")
  | gsub("&lt;"; "<")
  | gsub("&gt;"; ">")
  | gsub("&nbsp;"; " ");

{
  "_meta": {
    "show": "Gilmore Girls",
    "episode_count": length,
    "source": "TVmaze",
    "source_url": "https://www.tvmaze.com/shows/525/gilmore-girls/episodeguide",
    "license": "CC BY-SA"
  },
  "episodes": (
    map({
      key: ("s" + (.season | pad2) + "e" + (.number | pad2)),
      value: {
        title: .name,
        description: (.summary | clean_summary),
        airdate: .airdate,
        source_url: .url,
        featured: (.season == 1 and .number == 1)
      }
    })
    | from_entries
  )
}
