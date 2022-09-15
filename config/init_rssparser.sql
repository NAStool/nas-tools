INSERT OR IGNORE INTO "CONFIG_RSS_PARSER" ("ID", "NAME", "TYPE", "FORMAT", "PARAMS", "NOTE", "SYSDEF") VALUES ('1', '蜜柑计划', 'XML', '{
    "list": "/rss/channel/item",
    "torrent": {
        "title": {
            "path": ".//title/text()"
        },
        "enclosure": {
            "path": ".//enclosure[@type=''application/x-bittorrent'']/@url"
        },
        "link": {
            "path": ".//link/text()"
        },
        "description": {
            "path": ".//description/text()"
        },
        "size": {
            "path": ".//link/@length"
        }
    }
}', '', '', 'Y');
INSERT OR IGNORE INTO "CONFIG_RSS_PARSER" ("ID", "NAME", "TYPE", "FORMAT", "PARAMS", "NOTE", "SYSDEF") VALUES ('2', '通用', 'XML', '{
    "list": "/rss/channel/item",
    "torrent": {
        "title": {
            "path": ".//title/text()"
        },
        "enclosure": {
            "path": ".//enclosure[@type=''application/x-bittorrent'']/@url"
        },
        "link": {
            "path": ".//link/text()"
        },
        "description": {
            "path": ".//description/text()"
        },
        "size": {
            "path": ".//link/@length"
        }
    }
}', '', '', 'Y');